"""Download links from atlas measurements to the source code that computes them.

The packages are read in place from the project's ``packages/`` directory (no copies). When that
directory is not available (e.g. the container image), the links are simply not offered.
"""
from __future__ import annotations

import ast
import io
import os
import re
import tomllib
import zipfile
from functools import lru_cache
from pathlib import Path

PACKAGES = {
    'retinal-measures': {'module': 'retinal_measures', 'label': 'retinal-measures',
                         'summary': '측정 목록용 참조 측정 함수(안저·OCT·OCTA·FAF). mask·경계면·영상을 넣으면 값을 돌려줍니다.'},
    'ophthalmic-quantification': {'module': 'ophthalmic_quantification', 'label': 'ophthalmic-quantification',
                                  'summary': '프로젝트 정량화 패키지(안저 특징·병변 주석 계측·DR 지표).'},
}
SOURCE_TO_PACKAGE = {'정량화 패키지': 'ophthalmic-quantification', '병변 주석 계측': 'ophthalmic-quantification'}
ALLOWED_SUFFIXES = {'.py', '.md', '.toml', '.txt', '.cff'}
SKIP_PARTS = {'__pycache__', '.pytest_cache'}


def default_packages_root() -> Path | None:
    if configured := os.environ.get('RETINAL_ATLAS_PACKAGES_ROOT'):
        return Path(configured).expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / 'DOMAIN.yaml').is_file():
            return parent / 'packages'
    return None


class CodeIndex:
    def __init__(self, root: Path | None):
        self.root = root
        self.available = {name for name in PACKAGES if root and (root / name / 'pyproject.toml').is_file()}

    # ---- package files
    def package_dir(self, name: str) -> Path:
        return self.root / name

    def version(self, name: str) -> str:
        data = tomllib.loads((self.package_dir(name) / 'pyproject.toml').read_text(encoding='utf-8'))
        return data['project']['version']

    def files(self, name: str) -> list[Path]:
        base = self.package_dir(name)
        out = []
        for path in sorted(base.rglob('*')):
            rel = path.relative_to(base)
            if (path.is_file() and path.suffix in ALLOWED_SUFFIXES and not SKIP_PARTS & set(rel.parts)
                    and not any(p.endswith('.egg-info') for p in rel.parts) and not rel.parts[0].startswith('.')):
                out.append(rel)
        return out

    def safe_file(self, name: str, rel: str) -> Path | None:
        if name not in self.available:
            return None
        base = self.package_dir(name).resolve()
        target = (base / rel).resolve()
        if base not in target.parents or Path(rel) not in self.files(name):
            return None
        return target

    def zip_bytes(self, name: str) -> tuple[bytes, str]:
        top = f'{name}-{self.version(name)}'
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            for rel in self.files(name):
                z.write(self.package_dir(name) / rel, f'{top}/{rel.as_posix()}')
        return buf.getvalue(), f'{top}.zip'

    # ---- functions
    def module_file(self, name: str, module: str) -> Path:
        return Path('src') / PACKAGES[name]['module'] / f'{module.replace(".", "/")}.py'

    @lru_cache(maxsize=512)
    def function_source(self, dotted: str) -> dict | None:
        """``retinal_measures.lesions.area`` → file, line span and source text of that function."""
        if 'retinal-measures' not in self.available or not dotted.startswith('retinal_measures.'):
            return None
        module, func = dotted.removeprefix('retinal_measures.').rsplit('.', 1)
        rel = self.module_file('retinal-measures', module)
        path = self.package_dir('retinal-measures') / rel
        if not path.is_file():
            return None
        text = path.read_text(encoding='utf-8')
        for node in ast.parse(text).body:
            if isinstance(node, ast.FunctionDef) and node.name == func:
                start = min([node.lineno] + [d.lineno for d in node.decorator_list])
                lines = text.splitlines()[start - 1:node.end_lineno]
                return {'package': 'retinal-measures', 'file': rel.as_posix(), 'start': start, 'end': node.end_lineno,
                        'source': '\n'.join(lines), 'doc': ast.get_docstring(node) or ''}
        return None

    @lru_cache(maxsize=1)
    def metric_locations(self) -> dict[str, tuple[str, int]]:
        """Metric-name string literals in ophthalmic-quantification → first (file, line)."""
        if 'ophthalmic-quantification' not in self.available:
            return {}
        found = {}
        pattern = re.compile(r"""['"]([a-z0-9_]+)['"]""")
        for rel in self.files('ophthalmic-quantification'):
            if rel.suffix != '.py' or rel.parts[0] != 'src':
                continue
            for no, line in enumerate((self.package_dir('ophthalmic-quantification') / rel).read_text(encoding='utf-8').splitlines(), 1):
                for name in pattern.findall(line):
                    found.setdefault(name, (rel.as_posix(), no))
        return found

    def links_for(self, feature: dict) -> dict:
        """Download/view links for one atlas measurement feature."""
        impl = feature.get('impl', {})
        out = {'function': None, 'project': []}
        package = impl.get('package')
        if package and self.function_source(package['function']):
            out['function'] = package['function']
        pkgs = {SOURCE_TO_PACKAGE[s] for s in impl.get('sources', []) if s in SOURCE_TO_PACKAGE} & self.available
        if pkgs:
            locs = self.metric_locations()
            files = sorted({locs[e][0] for e in impl.get('examples', []) if e in locs})
            out['project'] = [{'package': 'ophthalmic-quantification', 'file': f} for f in files] or \
                             [{'package': 'ophthalmic-quantification', 'file': None}]
        return out
