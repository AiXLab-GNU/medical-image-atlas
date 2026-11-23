"""Download links from atlas measurements to the pathology-measures source code.

The package is read in place from the domain's ``packages/`` directory (no copies). When that directory
is not available (e.g. a container image), the links are simply not offered.
"""
from __future__ import annotations

import ast
import io
import os
import tomllib
import zipfile
from functools import lru_cache
from pathlib import Path

PACKAGES = {
    'pathology-measures': {'module': 'pathology_measures', 'label': 'pathology-measures',
                             'summary': 'H&E 조직 측정 참조 함수(조직 구성·글리슨 패턴 비율·샘 모양·내강·핵·질감). 영상과 주석 mask를 넣으면 값을 돌려줍니다.'},
}
ALLOWED_SUFFIXES = {'.py', '.md', '.toml', '.txt'}
SKIP_PARTS = {'__pycache__', '.pytest_cache'}


def default_packages_root() -> Path | None:
    if configured := os.environ.get('PATHOLOGY_ATLAS_PACKAGES_ROOT'):
        return Path(configured).expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / 'DOMAIN.yaml').is_file():
            return parent / 'packages'
    return None


class CodeIndex:
    def __init__(self, root: Path | None):
        self.root = root
        self.available = {name for name in PACKAGES if root and (root / name / 'pyproject.toml').is_file()}

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

    @lru_cache(maxsize=512)
    def function_source(self, dotted: str) -> dict | None:
        """``pathology_measures.mass.size`` → file, line span and source text of that function."""
        name = 'pathology-measures'
        if name not in self.available or not dotted.startswith('pathology_measures.'):
            return None
        module, func = dotted.removeprefix('pathology_measures.').rsplit('.', 1)
        rel = Path('src/pathology_measures') / f'{module}.py'
        path = self.package_dir(name) / rel
        if not path.is_file():
            return None
        text = path.read_text(encoding='utf-8')
        for node in ast.parse(text).body:
            if isinstance(node, ast.FunctionDef) and node.name == func:
                start = min([node.lineno] + [d.lineno for d in node.decorator_list])
                return {'package': name, 'file': rel.as_posix(), 'start': start, 'end': node.end_lineno,
                        'source': '\n'.join(text.splitlines()[start - 1:node.end_lineno]),
                        'doc': ast.get_docstring(node) or ''}
        return None

    def links_for(self, feature: dict) -> dict:
        package = feature.get('impl', {}).get('package')
        ok = bool(package and self.function_source(package['function']))
        return {'function': package['function'] if ok else None, 'project': []}
