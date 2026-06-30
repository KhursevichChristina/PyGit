from lab3.pygit.objects import Tree, Commit, hash_object, CommitHistoryIterator
from lab3.pygit.index import read_index, write_index
import os
import sys
from typing import Callable, Any, TypeVar, Generator

OBJECTS_DIR = os.path.join('.pygit', 'objects')
HEADS_DIR = os.path.join('.pygit', 'refs', 'heads')
HEAD_FILE = os.path.join('.pygit', 'HEAD')
FILE_MODE = '100644'
TREE_MODE = '040000'
T = TypeVar('T')

commands: dict[str, Any] = {}


def command(name: str) -> Callable[[T], T]:
    """Декоратор для добавления функции в словарь команд
    Args:
        name (str): имя команды

    Returns:
        декоратор
    """
    def decorator(func: T) -> T:
        commands[name] = func
        return func
    return decorator


@command('init')
def init() -> None:
    """Иницилизирует новый репозиторий

    Создает необходимые папки и файлы для работы репозитория
    """
    os.mkdir('.pygit')
    os.mkdir(OBJECTS_DIR)
    os.makedirs(HEADS_DIR)
    with open(HEAD_FILE, 'w') as head_file:
        head_file.write('ref: refs/heads/main')


@command('add')
def add(file_to_add: str) -> None:
    """Добавляет файл в индекс

    Args:
        file_to_add (str): путь к файлу для добавления в индекс
    """
    with open(file_to_add, 'rb') as new_file:
        data = new_file.read()

    sha = hash_object(data, 'blob')
    mode = FILE_MODE
    index = read_index()

    found = False

    for i, (one_path, one_sha, one_mode) in enumerate(index):
        if one_path == file_to_add:
            index[i] = (file_to_add, sha, mode)
            found = True
            break

    if not found:
        index.append((file_to_add, sha, mode))

    write_index(index)


def _recursion_tree(
 current_tree: dict[str, Any],
 path: str
) -> Generator[tuple[str, list[Any], list[str]], None, None]:
    """Генератор для рекурсивного обхода структуры директорий

    Args:
        current_tree (dict): текущее дерево (уровень) для обхода
        path (str): путь к текущему дереву (уровню)

    Yields:
        tuple: запись (path, files, dirs) для каждого уровня
    """
    for directory, next_tree in current_tree['dirs'].items():
        if path == '':
            next_path = directory
        else:
            next_path = os.path.join(path, directory)

        for files in _recursion_tree(next_tree, next_path):
            yield files

    yield path, current_tree['files'], list(current_tree['dirs'].keys())


def write_tree() -> str:
    """Строит tree объекты на основе текущего состояния индекса

    Returns:
        str: хеш корневого tree объекта
    """
    index = read_index()

    tree: dict[str, Any] = {'files': [], 'dirs': {}}

    for path, sha, mode in index:
        path_parts = path.split('/')
        current_dir = tree

        for directory in path_parts[:-1]:
            if directory not in current_dir['dirs']:
                current_dir['dirs'][directory] = {'files': [], 'dirs': {}}
            current_dir = current_dir['dirs'][directory]
        current_dir['files'].append((path_parts[-1], sha, mode))

    all_trees_sha: dict[str, str] = {}
    for path, files, dirs in _recursion_tree(tree, ''):
        data_for_tree = []

        for directory in dirs:
            if path == '':
                directory_path = directory
            else:
                directory_path = os.path.join(path, directory)

            directory_sha = all_trees_sha[directory_path]
            data_for_tree.append((TREE_MODE, directory_path, directory_sha))

        for file_path, file_sha, file_mode in files:
            data_for_tree.append((file_mode, file_path, file_sha))

        current_tree = Tree(data_for_tree)
        current_tree_sha = hash_object(current_tree.serialize(), 'tree')
        all_trees_sha[path] = current_tree_sha

    print(all_trees_sha[''])
    return all_trees_sha['']


@command('commit')
def commit(args: list[str]) -> None:
    """Создает новый коммит с текущим состоянием индекса

    Args:
        args (list[str]):
        аргументы команды. Последний аргумент - сообщение коммита
    """
    root_tree_sha = write_tree()
    with open('.pygit/HEAD', 'r') as head_file:
        current_head = head_file.read()

    head_path = current_head[current_head.find(' ') + 1:]
    full_head_path = os.path.join('.pygit', head_path)

    parent_commit_sha = None
    if os.path.exists(full_head_path):
        with open(full_head_path, 'r') as parent_commit_file:
            parent_commit_sha = parent_commit_file.read()

    new_commit = Commit(root_tree_sha, parent_commit_sha, 'author', args[-1])
    new_commit_sha = hash_object(new_commit.serialize(), 'commit')

    with open(full_head_path, 'w') as new_commit_file:
        new_commit_file.write(new_commit_sha)


@command('log')
def log() -> None:
    """Выводит историю коммитов от последнего к первому"""
    with open('.pygit/HEAD', 'r') as head_file:
        current_head = head_file.read()

    head_path = current_head[current_head.find(' ') + 1:]
    full_head_path = os.path.join('.pygit', head_path)

    with open(full_head_path, 'r') as last_commit_file:
        last_commit_sha = last_commit_file.read()

    for commit_information in CommitHistoryIterator(last_commit_sha):
        print(f'commit {commit_information[0]}')
        print(f'Author: {commit_information[1]}')
        print()
        print(commit_information[2])
        print()


def main() -> None:
    """Основная функция для работы с командами git"""
    if len(sys.argv) < 2:
        print('No command')
        return

    command_name = sys.argv[1]
    args = sys.argv[2:]

    if command_name in commands:
        commands[command_name](args)
    else:
        print(f'Unknown command: {command_name}')
        return
