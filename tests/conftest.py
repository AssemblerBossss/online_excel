# Регистрируем фабрики Excel-фикстур как плагин, чтобы они были доступны во всех тестах.
pytest_plugins = ("tests.fixtures.excel_factories",)
