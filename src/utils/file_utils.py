import logging
import os
import time

logger = logging.getLogger(__name__)


def cleanup_temp_files(file_paths: list[str], max_retries: int = 5, base_wait: float = 0.5) -> None:
    for fp in file_paths:
        removed = False
        for attempt in range(max_retries):
            try:
                if os.path.exists(fp):
                    os.remove(fp)
                removed = True
                break
            except PermissionError:
                wait = base_wait * (attempt + 1)
                logger.warning(
                    "Arquivo bloqueado, tentativa %s/%s em %.1fs: %s",
                    attempt + 1, max_retries, wait, fp,
                )
                time.sleep(wait)
            except OSError as e:
                if getattr(e, "winerror", None) == 32 and attempt < max_retries - 1:
                    wait = base_wait * (attempt + 1)
                    logger.warning(
                        "Arquivo em uso (WinError 32), tentativa %s/%s em %.1fs: %s",
                        attempt + 1, max_retries, wait, fp,
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"Não foi possível remover {fp}: {e}")
                    break
            except Exception as e:
                logger.error(f"Erro ao remover {fp}: {e}")
                break
        if not removed and os.path.exists(fp):
            logger.error(
                "Arquivo temporário não removido após retries (será ignorado): %s", fp
            )
