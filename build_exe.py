import os
import shutil
import PyInstaller.__main__


# Создаем папку Logs если её нет
logs_dir = os.path.join("./", "Logs")
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)
# Пути к данным
assets_dir = "./assets"
config_dir = "./config"
systems_dir = "./systems"
# Убираем Chrome и ChromeDriver из add-data!
add_data = [
    f"{os.path.join(assets_dir, '3571833.ico')}{os.pathsep}assets",
    f"{os.path.join(assets_dir, '3571833.png')}{os.pathsep}assets",
    f"{config_dir}{os.pathsep}config",
    f"{systems_dir}{os.pathsep}systems"
]
# Сборка аргументов для PyInstaller
args = [
    "main.py",
    "--onedir",
    "--windowed",
    "--name=AutoCheck",
    "--clean",
    "--noconfirm",
    f"--icon={os.path.join(assets_dir, '3571833.ico')}",
    "--distpath=./AutoCheck_steble",
    "--noupx",
    "--hidden-import=interfaces.ui",
    "--hidden-import=services.func_and_pass",
    "--hidden-import=services.logger",
    "--hidden-import=services.webdriver",
    "--hidden-import=systems.a.a",
    "--hidden-import=systems.g.g",
    "--hidden-import=systems.m.m",
    "--hidden-import=systems.mi.mi",
    "--hidden-import=systems.p.p",
    "--hidden-import=systems.k.k",
]
# Добавляем ресурсы
for data in add_data:
    args.append(f"--add-data={data}")
print("=== Начало сборки PyInstaller ===\n")
# Запускаем сборку
PyInstaller.__main__.run(args)
print("\n=== Сборка PyInstaller завершена ===")
print("=== Копирование Chrome и ChromeDriver ===\n")
# Пути для копирования
dist_dir = "./AutoCheck_steble/AutoCheck"
chrome_src = "./assets/chrome-win64"
chromedriver_src = "./assets/chromedriver-win64"
putty_dest = os.path.join(dist_dir, "PuTTY")
chrome_dest = os.path.join(dist_dir, "chrome-win64")
chromedriver_dest = os.path.join(dist_dir, "chromedriver-win64")
# Копируем Chrome
if os.path.exists(chrome_src):
    if os.path.exists(chrome_dest):
        shutil.rmtree(chrome_dest)
    print(f"Копирование Chrome из {chrome_src}...")
    shutil.copytree(chrome_src, chrome_dest)
    print(f"✓ Chrome скопирован в {chrome_dest}\n")
else:
    print(f"⚠ Внимание: {chrome_src} не найден!\n")
# Копируем ChromeDriver
if os.path.exists(chromedriver_src):
    if os.path.exists(chromedriver_dest):
        shutil.rmtree(chromedriver_dest)
    print(f"Копирование ChromeDriver из {chromedriver_src}...")
    shutil.copytree(chromedriver_src, chromedriver_dest)
    print(f"✓ ChromeDriver скопирован в {chromedriver_dest}\n")
else:
    print(f"⚠ Внимание: {chromedriver_src} не найден!\n")
print("=== Сборка полностью завершена ===")
print(f"\nЗапустите приложение: {os.path.join(dist_dir, 'AutoCheck.exe')}")
