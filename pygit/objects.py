import abc
import hashlib
import zlib
import os

SHA_LENGTH = 20


class GitObject(abc.ABC):
    """Базовый абстрактный класс для git объектов"""

    @abc.abstractmethod
    def serialize(self) -> bytes:
        """Сериализует объект в байты для хранения

        Returns:
            bytes: сериализованные данные объекта
        """
        pass

    @abc.abstractmethod
    def deserialize(self, data: bytes) -> None:
        """Десериализует объект из байтов

        Args:
            data (bytes): данные в виде байтов
        """
        pass


class Blob(GitObject):
    """Blob объект git. Представляет собой содержимое файла.

    Attributes:
        data (bytes): содержимое файла в виде байтов
    """

    def __init__(self, data: bytes) -> None:
        """Инициализирует blob объект с содержимым файла

        Args:
            data (bytes): содержимое файла в виде байтов
        """
        self.data = data

    def serialize(self) -> bytes:
        """Сериализует blob объект

        Returns:
            bytes: сериализованное содержимое файла
        """
        return self.data

    def deserialize(self, data: bytes) -> None:
        """Десериализует blob объект

        Args:
            data (bytes): сериализованные данные содержимого файла
        """
        self.data = data


class Tree(GitObject):
    """Tree объект. Хранит список указателей на другие blob и tree объекты

    Attributes:
        data (list[tuple[str, str, str]]): список записей (mode, path, sha)
    """

    def __init__(self, data: list[tuple[str, str, str]] | None = None) -> None:
        """Инициализирует tree объект с данными

        Args:
            data (list[tuple[str, str, str]]): список записей (mode, path, sha)
        """
        if data is None:
            data = []
        self.data = data

    def serialize(self) -> bytes:
        """Сериализует tree объект

        Returns:
            bytes: сериализованные данные
        """
        data_bytes = b''
        for mode, path, sha in self.data:
            mode_bytes = mode.encode('utf-8')
            path_bytes = path.encode('utf-8')
            sha_bytes = bytes.fromhex(sha)
            one_data_bytes = mode_bytes + b' ' + path_bytes + b'\0' + sha_bytes
            data_bytes += one_data_bytes
        return data_bytes

    def deserialize(self, data: bytes) -> None:
        """Десериализует tree объект

        Args:
            data (bytes): сериализованные данные
        """
        self.data = []
        index = 0
        while index < len(data):
            path_index = data.find(b' ', index)
            sha_index = data.find(b'\0', path_index)
            mode = data[index:path_index].decode('utf-8')
            path = data[path_index + 1:sha_index].decode('utf-8')
            sha = data[sha_index + 1:sha_index + 1 + SHA_LENGTH].hex()
            index = sha_index + 1 + SHA_LENGTH

            self.data.append((mode, path, sha))


class Commit(GitObject):
    """Commit объект. Представляет снимок в истории проекта

    Attributes:
        sha_tree (str): хеш корневого tree объекта
        sha_parent (str | None): хеш родительского коммита
        author (str): автор коммита
        message (str): сообщение коммита
    """

    def __init__(
            self,
            sha_tree: str = '',
            sha_parent: str | None = None,
            author: str = '',
            message: str = ''
    ) -> None:
        """Инициализирует commit объект
        Args:
            sha_tree (str): хеш корневого tree объекта
            sha_parent (str | None): хеш родительского коммита
            author (str): автор коммита
            message (str): сообщение коммита
        """
        self.sha_tree = sha_tree
        self.sha_parent = sha_parent
        self.author = author
        self.message = message

    def serialize(self) -> bytes:
        """Сериализует commit объект

        Returns:
            bytes: сериализованные данные коммита
        """
        commit_strings = ''

        commit_strings += f'tree {self.sha_tree}\n'
        if self.sha_parent:
            commit_strings += f'parent {self.sha_parent}\n'
        commit_strings += f'author {self.author}\n\n'
        commit_strings += self.message
        bytes_commit_strings = commit_strings.encode('utf-8')
        return bytes_commit_strings

    def deserialize(self, data: bytes) -> None:
        """Десериализует commit объект

        Args:
            data (bytes): сериализованные данные коммита
        """
        commit_strings = data.decode('utf-8')

        tree_index = commit_strings.find('tree ') + len('tree ')
        parent_index = commit_strings.find('\nparent ')
        author_index = commit_strings.find('\nauthor ')
        message_index = commit_strings.find('\n\n')

        if parent_index != -1:
            self.sha_tree = commit_strings[tree_index:parent_index]
        else:
            self.sha_tree = commit_strings[tree_index:author_index]

        if parent_index != -1:
            self.sha_parent = commit_strings[
              parent_index
              + len('\nparent '):author_index
            ]
        else:
            self.sha_parent = None

        self.author = commit_strings[
          author_index
          + len('\nauthor '):message_index
        ]
        self.message = commit_strings[message_index + len('\n\n'):]


class CommitHistoryIterator:
    """Класс-итератор по истории коммитов

    Attributes:
        current_sha (str): текущий хеш коммита
    """

    def __init__(self, sha: str | None) -> None:
        """Инициализирует Класс-итератор с начальным хешем коммита

        Args:
            sha (str): хеш начального коммита
        """
        self.current_sha = sha

    def __iter__(self) -> 'CommitHistoryIterator':
        """Возвращает итератор

        Returns:
            CommitHistoryIterator: итератор
        """
        return self

    def __next__(self) -> tuple[str, str, str]:
        """Возвращает следующий в истории коммит

        Returns:
            tuple[str, str, str]:
            информация о коммите (sha_tree, author, message)

        Raises:
            StopIteration: когда достигнут конец истории коммитов
        """
        if not self.current_sha:
            raise StopIteration

        sha = self.current_sha

        if not sha:
            raise StopIteration

        path = os.path.join('.pygit', 'objects', sha[:2], sha[2:])

        with open(path, 'rb') as commit_file:
            compressed_commit = commit_file.read()

        current_commit = zlib.decompress(compressed_commit)
        data = current_commit[current_commit.find(b'\0') + 1:]
        commit = Commit()
        commit.deserialize(data)
        commit_information = (commit.sha_tree, commit.author, commit.message)
        if commit.sha_parent:
            self.current_sha = commit.sha_parent
        else:
            self.current_sha = None

        return commit_information


def hash_object(data: bytes, obj_type: str) -> str:
    """Вычисляяет хеш для git объекта

    Args:
        data (bytes): данные объекта для хеширования
        obj_type (str): тип git объекта
    Returns:
        str: хеш git объекта
    """
    title = f'{obj_type} {len(data)}\0'.encode('utf-8')
    data_with_title = title + data
    sha = hashlib.sha1(data_with_title).hexdigest()

    compressed_data = zlib.compress(data_with_title)
    object_directory = os.path.join('.pygit/objects', sha[:2])
    os.makedirs(object_directory, exist_ok=True)

    path_compressed_data_file = os.path.join(object_directory, sha[2:])

    with open(path_compressed_data_file, 'wb') as compressed_data_file:
        compressed_data_file.write(compressed_data)

    return sha
