"""Пакет UI. Реэкспорт CtOSApplication/run_ctos сюда не делаем: application.py
зависит от ctos.modules.registry, который зависит от ctos.ui.theme — эта
зависимость затягивается в ctos/ui/__init__.py и ломает прямой импорт любого
модуля (например `from ctos.modules.zero_day import ZeroDownModule`) циклическим
импортом. Импортируйте напрямую: `from ctos.ui.app import run_ctos`.
"""
