import logging

from gateways.sonarqube import (
    CheckResult,
    Bugs,
    CodeSmells,
    Vulnerabilities,
    SonarQubeResults,
)

logger = logging.getLogger("api")


class SonarqubeService:
    async def check_zip(self, zip_file: bytes) -> SonarQubeResults:
        """
        Фиктивный метод для анализа ZIP-файла и возврата результатов SonarQube.

        Args:
            zip_file (bytes): Содержимое ZIP-файла в виде байтов.

        Returns:
            SonarQubeResults: Результаты анализа в формате Pydantic-схемы.
        """
        logger.info("Запуск фиктивного анализа SonarQube для ZIP-файла")
        # TODO запрос и получение данных у внешнего сервиса

        # Формируем фиктивные результаты в формате Pydantic-схем
        check_result = CheckResult(
            overall_coverage=85.5,
            bugs=Bugs(total=12, critical=2, major=5, minor=5),
            code_smells=CodeSmells(total=20, critical=3, major=10, minor=7),
            vulnerabilities=Vulnerabilities(total=4, critical=1, major=2, minor=1),
        )

        results = SonarQubeResults(sonarqube=check_result)

        logger.info(f"Результаты SonarQube: {results}")
        return results
