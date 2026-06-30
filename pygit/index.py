import os

INDEX_PATH = os.path.join('.pygit', 'index')


def read_index() -> list[tuple[str, str, str]]:
    """Читает файл индекс

    Returns:
        list[tuple[str, str, str]]: Список записей индекса (path, sha, mode)
    """
    index: list[tuple[str, str, str]] = []
    if not os.path.exists(INDEX_PATH):
        return index

    with open(INDEX_PATH, 'r') as index_file:
        for line in index_file:
            mode_index = line.find(' ')
            path_index = line.find(' ', mode_index + 1)
            sha = line[:mode_index]
            mode = line[mode_index + 1:path_index]
            path = line[path_index + 1:]
            index.append((path, sha, mode))

    return index


def write_index(index: list[tuple[str, str, str]]) -> None:
    """Записывает данные в индекс

    Args:
        index (list[tuple[str, str, str]]): список записей (path, sha, mode)
    """
    with open(INDEX_PATH, 'w') as index_file:
        for path, sha, mode in index:
            index_file.write(f'{sha} {mode} {path}\n')
