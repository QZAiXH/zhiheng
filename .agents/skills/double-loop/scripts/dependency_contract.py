"""初始化与运行预检共用的依赖清单及内容指纹。"""

import hashlib
import json
from pathlib import Path


MANIFEST_PATH = Path(__file__).resolve().parents[1] / "assets" / "project-manifest.json"


def manifest():
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != 1 or value.get("repo") != "mattpocock/skills":
        raise ValueError("不支持的项目依赖清单。")
    return value


def tree_hash(path):
    """内容指纹覆盖引用和脚本；忽略宿主产生的缓存，拒绝越界链接。"""
    root = Path(path).resolve()
    if not root.is_dir():
        raise ValueError(f"技能目录不存在：{path}")
    files = {}
    for entry in sorted(root.rglob("*")):
        relative = entry.relative_to(root)
        if any(part in {"__pycache__", ".git", ".DS_Store"} for part in relative.parts) \
                or entry.suffix == ".pyc":
            continue
        if entry.is_symlink() and (entry.is_dir() or not entry.resolve().is_relative_to(root)):
            raise ValueError(f"技能含目录链接或越界链接：{relative}")
        if entry.is_file():
            files[relative.as_posix()] = hashlib.sha256(entry.read_bytes()).hexdigest()
        elif not entry.is_dir():
            raise ValueError(f"技能含不支持的文件类型：{relative}")
    if "SKILL.md" not in files:
        raise ValueError(f"缺少 SKILL.md：{path}")
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def check_installed(config):
    """旧 checkout 配置继续可用；新安装配置须逐项匹配固定源和记录。"""
    installed = config.get("installed_skills")
    if installed is None:
        return
    required = manifest()["skills"]
    if not isinstance(installed, dict) or set(installed) != set(required):
        raise ValueError("项目安装记录未覆盖完整上游技能清单。")
    source = Path(config["mattpocock_root"])
    for name, group in required.items():
        record = installed[name]
        path = Path(record["path"])
        if not path.is_absolute() or path.is_symlink():
            raise ValueError(f"安装路径必须是实际绝对目录：{name}")
        expected = tree_hash(source / "skills" / group / name)
        if record.get("sha256") != expected or tree_hash(path) != expected:
            raise ValueError(f"项目技能内容与固定版本不一致：{name}")
