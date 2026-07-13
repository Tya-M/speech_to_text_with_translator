#!/usr/bin/env python3
import os
import argparse
import sys

# --- КОНФИГУРАЦИЯ ---
BASE_OUTPUT_NAME = "project_full_code"
OUTPUT_EXTENSION = ".md"
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Папки, которые нужно игнорировать
IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', 'dist', 'build', 
    '.idea', '.vscode', 'venv', 'env', '.next', '.nuxt'
    # 'vendor' удалено из списка
}

# Файлы, которые нужно игнорировать
IGNORE_FILES = {
    '.DS_Store', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    'composer.lock', os.path.basename(__file__)
}

# Расширения файлов, которые мы хотим включить
INCLUDE_EXTENSIONS = {
    '.php', '.js', '.jsx', '.ts', '.tsx', '.py',
    '.json', '.scss', '.css', '.html', '.md', '.txt',
    '.sh', '.yaml', '.yml', '.sql', '.conf', '.env', 
    '.java', '.c', '.cpp', '.h', '.go', '.rs'
}

# Маппинг расширений для подсветки синтаксиса в Markdown
EXT_TO_LANG = {
    '.js': 'javascript', '.jsx': 'javascript',
    '.ts': 'typescript', '.tsx': 'typescript',
    '.php': 'php',
    '.py': 'python',
    '.scss': 'scss',
    '.css': 'css',
    '.json': 'json',
    '.html': 'html',
    '.md': 'markdown',
    '.sh': 'bash',
    '.yaml': 'yaml', '.yml': 'yaml',
    '.sql': 'sql',
    '.conf': 'nginx',
    '.java': 'java',
    '.c': 'c', '.cpp': 'cpp', '.h': 'c',
    '.go': 'go',
    '.rs': 'rust'
}

HEADER_BASE = "# Project Codebase Dump"

class RotatingFileWriter:
    """
    Класс для записи данных с автоматической разбивкой на файлы 
    при достижении лимита размера.

    Имя файла-части (_partN) и заголовок "(Part N)" добавляются всегда,
    но при закрытии, если получилась только ОДНА часть, файл переименовывается
    в base.md, а из заголовка убирается пометка "(Part 1)".
    """
    def __init__(self, base_name, extension, max_bytes):
        self.base_name = base_name
        self.extension = extension
        self.max_bytes = max_bytes
        self.part_num = 0
        self.current_file = None
        self.current_filename = None
        self.current_size = 0
        self.created_files = []
        self.final_files = []
        self._open_new_file()

    def _get_part_filename(self, part_num):
        # Формируем имя: base_part1.md, base_part2.md и т.д.
        return f"{self.base_name}_part{part_num}{self.extension}"

    def _get_single_filename(self):
        # Имя для случая, когда часть всего одна: base.md
        return f"{self.base_name}{self.extension}"

    def _open_new_file(self):
        if self.current_file:
            self.current_file.close()

        self.part_num += 1
        filename = self._get_part_filename(self.part_num)
        self.current_file = open(filename, 'w', encoding='utf-8')
        self.current_filename = filename
        self.created_files.append(filename)
        self.current_size = 0
        print(f"Created new file chunk: {filename}")
        
        # Добавляем заголовок в начало каждого тома для ясности
        header = f"{HEADER_BASE} (Part {self.part_num})\n\n"
        self.current_file.write(header)
        self.current_size += len(header.encode('utf-8'))

    def write(self, data):
        data_bytes = data.encode('utf-8')
        data_len = len(data_bytes)

        # Если текущий файл не пустой (кроме заголовка) и добавление данных 
        # превысит лимит, переключаемся на новый файл.
        # Проверка self.current_size > 100 нужна, чтобы не зациклиться, 
        # если один кусок данных больше чем весь лимит файла.
        if (self.current_size + data_len > self.max_bytes) and (self.current_size > 100):
            self._open_new_file()
            # После открытия нового файла рекурсивно вызываем write, 
            # чтобы записать данные в новый файл
            self.write(data) 
        else:
            self.current_file.write(data)
            self.current_size += data_len

    def close(self):
        if self.current_file:
            self.current_file.close()
            self.current_file = None

        # Если получилась всего одна часть — убираем суффикс _part1 из имени
        # и пометку "(Part 1)" из заголовка.
        if self.part_num == 1:
            single_part_path = self._get_part_filename(1)
            final_path = self._get_single_filename()
            try:
                with open(single_part_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                content = content.replace(
                    f"{HEADER_BASE} (Part 1)\n\n",
                    f"{HEADER_BASE}\n\n",
                    1
                )

                with open(final_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                if os.path.abspath(single_part_path) != os.path.abspath(final_path):
                    os.remove(single_part_path)

                self.final_files = [final_path]
            except FileNotFoundError:
                self.final_files = []
        else:
            self.final_files = list(self.created_files)

def is_text_file(filename):
    """Проверка, нужно ли обрабатывать этот файл по расширению."""
    _, ext = os.path.splitext(filename)
    return ext.lower() in INCLUDE_EXTENSIONS

def get_language(filename):
    """Определение языка для code block."""
    _, ext = os.path.splitext(filename)
    return EXT_TO_LANG.get(ext.lower(), '')

def _path_components(path):
    """Разбивает путь на компоненты, игнорируя '' и '.'."""
    norm = path.replace('\\', '/')
    return tuple(p for p in norm.split('/') if p not in ('', '.'))

def build_exclusions(exclude_items):
    """
    Разбирает список исключений из командной строки на три группы:
      - exclude_names: исключение по имени файла/папки в любом месте дерева
        (элемент без разделителя пути, например 'tests' или 'config.php');
      - exclude_rel_suffixes: исключение по относительному пути (например 'src/legacy');
        совпадение проверяется по суффиксу компонентов пути,
        поэтому 'src/legacy' совпадёт с любым '.../src/legacy';
      - exclude_abs_paths: исключение по абсолютному пути.
    """
    exclude_names = set()
    exclude_rel_suffixes = []
    exclude_abs_paths = set()
    for item in exclude_items:
        if not item:
            continue
        has_sep = ('/' in item) or (os.sep in item)
        if os.path.isabs(item):
            exclude_abs_paths.add(os.path.normpath(os.path.abspath(item)))
        elif has_sep:
            comps = _path_components(item)
            if comps:
                exclude_rel_suffixes.append(comps)
        else:
            exclude_names.add(item)
    return exclude_names, exclude_rel_suffixes, exclude_abs_paths

def is_excluded(full_path, name, exclude_names, exclude_rel_suffixes, exclude_abs_paths):
    """Проверяет, попадает ли файл/папка под одно из правил исключения."""
    if name in exclude_names:
        return True

    abs_norm = os.path.normpath(os.path.abspath(full_path))
    if abs_norm in exclude_abs_paths:
        return True

    if exclude_rel_suffixes:
        rel_comps = _path_components(abs_norm)
        for comps in exclude_rel_suffixes:
            n = len(comps)
            if n <= len(rel_comps) and rel_comps[-n:] == comps:
                return True

    return False

def process_file(filepath, writer):
    """Читает один файл и передает его содержимое в writer."""
    try:
        rel_path = os.path.relpath(filepath, os.getcwd())
    except ValueError:
        rel_path = filepath

    print(f"Processing: {rel_path}")

    try:
        with open(filepath, 'r', encoding='utf-8') as infile:
            content = infile.read()
            
            # Формируем буфер для записи (заголовок + код + подвал)
            buffer = []
            buffer.append(f"## File: `{rel_path}`\n\n")
            
            lang = get_language(filepath)
            buffer.append(f"```{lang}\n")
            buffer.append(content)
            
            if content and not content.endswith('\n'):
                buffer.append('\n')
            
            buffer.append("```\n\n")
            buffer.append("---\n\n")
            
            # Пишем весь блок файла за один раз, чтобы минимизировать разрывы посередине
            writer.write("".join(buffer))
            
    except Exception as e:
        print(f"Error reading {rel_path}: {e}")
        error_msg = f"> Error reading file: {rel_path}\n> Reason: {e}\n\n"
        writer.write(error_msg)

def prompt_excluded_dir_names():
    """
    Интерактивно спрашивает у пользователя имена ПАПОК (через запятую),
    которые нужно исключить из объединения. Касается только папок,
    не файлов. Пустой ввод (Enter) — ничего не исключать.

    Имена сопоставляются по имени папки в любом месте дерева.
    Если ввод недоступен (неинтерактивный запуск) — возвращает пустой набор.
    """
    try:
        raw = input(
            "В��едите имена папок для исключения через запятую "
            "(или Enter, чтобы ничего не исключать): "
        )
    except EOFError:
        return set()

    names = set()
    for part in raw.split(','):
        name = part.strip()
        if name:
            names.add(name)
    return names

def process_directory(directory, writer, exclude_names, exclude_rel_suffixes, exclude_abs_paths, exclude_dir_names):
    """Рекурсивно обходит директорию и обрабатывает файлы."""
    for root, dirs, files in os.walk(directory):
        # Исключаем игнорируемые папки (по умолчанию + интерактивные + пользовательские)
        kept_dirs = []
        for d in dirs:
            if d in IGNORE_DIRS or d in exclude_dir_names:
                continue
            if is_excluded(os.path.join(root, d), d, exclude_names, exclude_rel_suffixes, exclude_abs_paths):
                continue
            kept_dirs.append(d)
        dirs[:] = kept_dirs
        
        for file in sorted(files):
            if file in IGNORE_FILES:
                continue
            if is_excluded(os.path.join(root, file), file, exclude_names, exclude_rel_suffixes, exclude_abs_paths):
                continue
            
            # Доп. проверка чтобы не читать ��ами файлы дампа, если они уже существуют
            if file.startswith(BASE_OUTPUT_NAME) and file.endswith(OUTPUT_EXTENSION):
                continue
            
            if not is_text_file(file):
                continue

            filepath = os.path.join(root, file)
            process_file(filepath, writer)

def main():
    parser = argparse.ArgumentParser(
        description="Слияние исходного кода в Markdown файлы (с разбивкой по 5 МБ)."
    )
    parser.add_argument(
        "paths", 
        nargs="*", 
        help="Пути к файлам или папкам для слияния. Если пусто, используется текущая директория."
    )
    parser.add_argument(
        "-e", "--exclude",
        action="append",
        default=[],
        metavar="ИМЯ_ИЛИ_ПУТЬ",
        help=("Файл или папка, которые нужно исключить из объединения. "
              "Можно указать имя (например, tests или config.php) — оно будет "
              "исключено в любом месте дерева, либо путь (например, "
              "src/legacy). Опцию можно повторять несколько раз.")
    )
    
    args = parser.parse_args()
    target_paths = args.paths if args.paths else ["."]
    exclude_names, exclude_rel_suffixes, exclude_abs_paths = build_exclusions(args.exclude)

    # Интерактивный вопрос: какие папки исключить (только папки, не файлы)
    exclude_dir_names = prompt_excluded_dir_names()

    print(f"Starting generation. Max size per file: {MAX_FILE_SIZE_MB} MB")
    if exclude_dir_names:
        print(f"Excluding folders: {', '.join(sorted(exclude_dir_names))}")
    if exclude_names:
        print(f"Excluding names: {', '.join(sorted(exclude_names))}")
    if exclude_rel_suffixes:
        print(f"Excluding paths: {', '.join('/'.join(c) for c in exclude_rel_suffixes)}")
    if exclude_abs_paths:
        print(f"Excluding absolute paths: {', '.join(sorted(exclude_abs_paths))}")
    
    writer = RotatingFileWriter(BASE_OUTPUT_NAME, OUTPUT_EXTENSION, MAX_FILE_SIZE_BYTES)

    try:
        for path in target_paths:
            base = os.path.basename(os.path.normpath(path))
            if is_excluded(path, base, exclude_names, exclude_rel_suffixes, exclude_abs_paths):
                print(f"Skipping excluded path: {path}")
                continue

            if os.path.isfile(path):
                if os.path.basename(path) not in IGNORE_FILES:
                     process_file(path, writer)
            elif os.path.isdir(path):
                process_directory(path, writer, exclude_names, exclude_rel_suffixes, exclude_abs_paths, exclude_dir_names)
            else:
                print(f"Warning: Path not found: {path}")

    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        writer.close()
        if writer.final_files:
            print(f"\nSuccess! Files created: {', '.join(writer.final_files)}")
        else:
            print("\nFinished, but no output files were created.")

if __name__ == "__main__":
    main()
