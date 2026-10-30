from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from moneyplease.db.models import Profile as ProfileRow
from moneyplease.matching.embed import Embedder
from moneyplease.matching.llm import LLMProvider
from moneyplease.profile.extract import pdf_text, redact
from moneyplease.profile.generate import draft_from_text
from moneyplease.profile.schema import Profile


class ProfileError(Exception):
    """El YAML del perfil no se puede leer o no es válido."""


def write_yaml(profile: Profile, path: Path, force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} ya existe; usa --force para sobrescribirlo")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(profile.model_dump(), allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def read_yaml(path: Path) -> Profile:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ProfileError(f"YAML inválido en {path}: {exc}") from exc
    try:
        return Profile.model_validate(data)
    except ValidationError as exc:
        problems = "\n".join(f"  {'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
        raise ProfileError(f"Perfil inválido en {path}:\n{problems}") from exc


def save(session: Session, profile: Profile, cv_text: str, embedder: Embedder) -> ProfileRow:
    last = session.scalar(select(ProfileRow.version).order_by(ProfileRow.version.desc()).limit(1))
    row = ProfileRow(version=(last or 0) + 1, cv_texto=cv_text, perfil_json=profile.model_dump(),
                     embedding=embedder.embed([profile.embedding_text()])[0], creado_en=datetime.now(UTC))
    session.add(row)
    session.commit()
    return row


def active(session: Session) -> ProfileRow | None:
    return session.scalars(select(ProfileRow).order_by(ProfileRow.version.desc()).limit(1)).first()


def from_cv(pdf: Path, private_dir: Path, llm: LLMProvider, force: bool) -> Path:
    out = private_dir / "profile.yaml"
    if out.exists() and not force:
        raise FileExistsError(f"{out} ya existe; usa --force para sobrescribirlo")
    redacted = redact(pdf_text(pdf))
    private_dir.mkdir(parents=True, exist_ok=True)
    (private_dir / "cv.txt").write_text(redacted, encoding="utf-8")
    write_yaml(draft_from_text(redacted, llm), out, force=force)
    return out
