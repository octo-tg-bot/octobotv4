@echo off
pybabel extract plugins base_plugins -o locales/base.pot -k localize -k nlocalize -k localizable
pybabel update -d locales -i locales/base.pot
pybabel compile -d locales