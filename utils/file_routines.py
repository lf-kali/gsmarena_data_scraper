import os

import shutil

import json

from typing import Type, Callable


class FormattedSize:
    __LABELS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    __BASE = 1024

    def __init__(self, num, txt):
        self._num = num

        if txt.upper() in FormattedSize.__LABELS:
            self._txt = txt
        else:
            raise ValueError(f'Unidade de tamanho inexistente: {txt}')

    def tobytes(self):
        for exp in range(6, 0, -1):
            idx = exp - 1
            if FormattedSize.__LABELS[idx] == self._txt:
                return int(self._num * FormattedSize.__BASE ** exp)

    def tostr(self):
        return f'{self._num}{self._txt}'

    @property
    def num(self):
        return self._num

    @property
    def txt(self):
        return self._txt

    @classmethod
    def frombytes(cls, size: int):
        for exp, label in enumerate(cls.__LABELS):
            next_size = cls.__BASE ** (exp + 1)
            if size < next_size:
                tamanho = float(size / cls.__BASE ** exp)
                return cls(round(tamanho, 2), label)

    @classmethod
    def fromstr(cls, txt: str):
        txt = txt.upper().replace(' ', '')

        for i, char in enumerate(txt):
            if not (char.isdigit() or char == '.'):
                break
        else:
            raise ValueError(f'Não foi possível identificar a unidade em {txt}.')

        num_str = txt[:i]
        label = txt[i:]

        try:
            num = float(num_str)
        except ValueError:
            raise ValueError(f'{num_str} não é um número válido.')

        if label not in cls.__LABELS:
            raise ValueError(f'Unidade de tamanho inexistente: {label}')

        return cls(num, label)

    def __str__(self):
        return f'{self._num}{self._txt}'


class Arquivo:
    def __init__(self, caminho: str):
        self._caminho = caminho
        self._raiz, self._nome = os.path.split(caminho)
        self._stem, self._extensao = os.path.splitext(self._nome)
        self._tamanho = os.path.getsize(caminho)

    @property
    def caminho(self):
        return self._caminho

    @property
    def raiz(self):
        return self._raiz

    @property
    def nome(self):
        return self._nome

    @property
    def stem(self):
        return self._stem

    @property
    def extensao(self):
        return self._extensao

    @property
    def tamanho(self):
        return self._tamanho

    def formatar_tamanho(self):
        tamanho = FormattedSize.frombytes(self._tamanho)
        return tamanho.tostr()

    def mover(self, destino: str):
        novo_caminho = os.path.join(destino, self.nome)
        shutil.move(self._caminho, novo_caminho)

    def copiar(self, destino: str):
        novo_nome = f"{self._stem}_copy{self._extensao}"
        novo_caminho = os.path.join(destino, novo_nome)
        shutil.copy(self.caminho, novo_caminho)

    def excluir(self):
        os.remove(self.caminho)

    def renomear(self, nova_stem):
        novo_nome = f'{nova_stem}{self.extensao}'
        novo_caminho = os.path.join(self.raiz, novo_nome)
        os.rename(self.caminho, novo_caminho)
        self._caminho = novo_caminho
        self._raiz, self._nome = os.path.split(novo_caminho)
        self._stem = nova_stem

    def to_dict(self):
        data = {
            'name':self.nome,
            'dir':self.raiz,
            'path':self.caminho,
            'size':self.formatar_tamanho()
        }
        return data

    def __repr__(self):
        return f'Nome: {self.nome}, Tamanho: {self.formatar_tamanho()}, Caminho: {self.caminho}'


class FileGroup(list):
    def __init__(self, group: list[Arquivo]):
        tests = [isinstance(item, Arquivo) for item in group]
        if not all(tests):
            raise TypeError
        super().__init__(group)

    def mover_todos(self, destino: str):
        for arquivo in self:
            arquivo.mover(destino)

    def copiar_todos(self, destino: str):
        for arquivo in self:
            arquivo.copiar(destino)

    def excluir_todos(self):
        for arquivo in self:
            arquivo.excluir()

    def renomear_todos(self, nova_stem: str):
        for i, arquivo in enumerate(self):
            arquivo.renomear(f'{nova_stem}_{i}')



class Filter:
    FILTER_TYPES = {
        'tags': (tuple, list),
        'extensions': (tuple, list),
        'tamanho_min': (str,),
        'tamanho_max': (str,)
    }

    def __init__(self, filter_type:str, value):
        if filter_type not in Filter.FILTER_TYPES.keys():
            raise ValueError(f'{filter_type} não é um tipo de filtro reconhecido.')

        self.__filter_type = filter_type

        expected_types = Filter.FILTER_TYPES[self.__filter_type]
        value_typecheck = isinstance(value, expected_types)

        if not value_typecheck:
            raise TypeError(f'{type(value)} value type is not valid for "{self.__filter_type}" '
                            f'filter type\nCorrect type: {expected_types}')

        if 'tamanho' in self.__filter_type:
            try:
                self.__value = FormattedSize.fromstr(value)
            except ValueError:
                raise ValueError(f'{value} is not a valid file size.')
        else:
            self.__value = value

    @property
    def filter_type(self):
        return self.__filter_type

    @property
    def value(self):
        return self.__value

    def match(self, arquivo:Arquivo):
        filter_testing = {
            'tags': lambda a: any(tag.upper().strip() in a.stem.upper() for tag in self.__value),
            'extensions': lambda a: any(extension.lower().strip() == a.extensao for extension in self.__value),
            'tamanho_min': lambda a: a.tamanho >= self.__value.tobytes(),
            'tamanho_max': lambda a: a.tamanho <= self.__value.tobytes()
        }

        return filter_testing[self.__filter_type](arquivo)


class FilterList(list):
    def __init__(self, filters:list[Filter]):
        tests = [isinstance(filefilter, Filter) for filefilter in filters]
        if not all(tests):
            raise TypeError
        
        super().__init__(filters)

    def match_all(self, file:Arquivo):
        tests = [filefilter.match(file) for filefilter in self]

        return all(tests)

    @classmethod
    def from_dict(cls, data):
        return cls([Filter(key, value) for key, value in data.items()])

    @classmethod
    def ignore_invalid(cls, **data):
        valid = []
        for key, value in data.items():
            if value in ('', [], [''], None):
                continue
            try:
                valid.append(Filter(key, value))
            except ValueError:
                continue
        return cls(valid)

    def to_dict(self):
        data = {}
        for filefilter in self:
            data.update({filefilter.filter_type:filefilter.value})

        return data


class Menu:
    def __init__(self, titulo: str, *opcoes):
        self.titulo = titulo
        self.opcoes = opcoes

    def exibir(self):
        print('=' * 80)
        print(f'    {self.titulo}')
        print('=' * 80)
        for i, (texto, _) in enumerate(self.opcoes, start=1):
            print(f'\033[32m{i}\033[m - \033[34m{texto}\033[m')
        print('=' * 40)

    def escolher(self):
        while True:
            try:
                opc = int(input('Selecionar opção: '))
                if 1 <= opc <= len(self.opcoes):
                    return opc
                else:
                    print('Opção inválida!')
            except ValueError:
                print('Opção inválida!')

    def executar(self):
        while True:
            self.exibir()
            escolher = self.escolher() - 1
            _, acao = self.opcoes[escolher]
            if acao is None:
                break
            acao()


class FileSearch:
    def __init__(self, dirpath, **filters):
        self.dirpath = os.path.normpath(dirpath)
        self.filters = FilterList.ignore_invalid(**filters)
        self.__results = []

    def run(self):
        varredura = list(os.walk(self.dirpath))
        for raiz, _, arquivos in varredura:
            for arquivo in arquivos:
                arquivo = Arquivo(str(os.path.join(raiz,arquivo)))

                if not self.filters or self.filters.match_all(arquivo):
                    self.__results.append(arquivo)

    def get_results(self, to_dict = False):
        return FileGroup(self.__results) if not to_dict else [f.to_dict() for f in self.__results]


class OrganizingRoutine:
    __routines_dir = r'./routines' #linkar ao config.json mais tarde

    def __init__(self, name = 'NewRoutine', task_sources:list = None):
        self.__task_sources = [] if task_sources is None else task_sources
        self.__compiled_tasks = []
        self.__stem = name
        self.__filename = self.__stem+'.json'
        self.__path = str(os.path.join(OrganizingRoutine.__routines_dir, self.__filename))

    @property
    def name(self):
        return self.__stem

    def new_task(self, action, dirpath, **filters):
        if action not in organizing_actions.keys():
            raise ValueError('invalid action name')

        self.__task_sources.append({
            'action':action,
            'dirpath':dirpath,
            'filters':{**filters}
        })

        self.compile_tasks()

    def compile_tasks(self):
        for i, d_task in enumerate(self.__task_sources):
            if i < len(self.__compiled_tasks):
                continue

            action_name = d_task['action']
            dirpath = d_task['dirpath']
            filters = d_task['filters']

            search = FileSearch(dirpath, **filters)
            action = organizing_actions[action_name]

            self.__compiled_tasks.append((search, action))

    def run(self):
        for task in self.__compiled_tasks:
            search, action = task
            search.run()
            results = search.get_results()
            action(results)

    def export(self):
        os.makedirs(OrganizingRoutine.__routines_dir, exist_ok=True)
        data = {'name':self.name, 'task_sources':self.__task_sources}

        try:
            with open(self.__path, 'w+', encoding='utf-8') as r:
                json.dump(data, r, indent=True, ensure_ascii=False)

        except Exception as e:
            print(f'ERRO: {e}')

    @classmethod
    def from_json(cls, name:str):
        routine_filename = name+'.json'
        routine_path = str(os.path.join(cls.__routines_dir, routine_filename))

        try:
            with open(routine_path, 'r', encoding='utf-8') as r_file:
                data = json.load(r_file)

                routine = cls(**data)
                routine.compile_tasks()

                return routine

        except FileNotFoundError:
            raise FileNotFoundError(f'No routine named "{name}"')


def is_serializable(obj):
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False


def adiar_execucao(func, *args, **kwargs):
    def wrapper():
        return func(*args, **kwargs)

    return wrapper


def adiar_input_dict(dic: dict, chave: str, valuetype: Type = None, factorymethod: Callable = None):
    # noinspection PyCallingNonCallable
    def wrapper():
        while True:
            valor_str = input(f'{chave.replace('_', ' ').capitalize()}: ')
            try:
                valor_convertido = valuetype(valor_str) if factorymethod is None else factorymethod(valor_str)
                dic.update({chave: valor_convertido})
                break
            except ValueError:
                print('Entrada inválida!')

    return wrapper


def ler_caminho(prompt):
    while True:
        caminho = os.path.normpath(input(prompt).strip())
        caminho_valido = os.path.exists(caminho)
        if not caminho_valido:
            print(f'\033[31mERRO\033[m: Caminho "\033[31m{caminho}\033[m" é inválido!')
        else:
            return caminho


def mover_resultados(arquivos:FileGroup):
    destino = input('Novo caminho: ')
    arquivos.mover_todos(destino)


def copiar_resultados(arquivos:FileGroup):
    destino = input('Novo caminho: ')
    arquivos.copiar_todos(destino)


def excluir_resultados(arquivos:FileGroup):
    arquivos.excluir_todos()


def renomear_resultados(arquivos:FileGroup):
    nova_stem = input('Novo nome padrão para os arquivos: ')
    arquivos.renomear_todos(nova_stem)


reg = {
    'FormattedSize':FormattedSize,
    'Arquivo':Arquivo,
    'FileGroup':FileGroup,
    'FileSearch': FileSearch,
    'Filter':Filter,
    'FilterList':FilterList,
    'Menu':Menu,
    'is_serializable':is_serializable,
    'adiar_execucao':adiar_execucao,
    'adiar_input_dict':adiar_input_dict,
    'ler_caminho':ler_caminho,
}


organizing_actions = {
    'mover_resultados':mover_resultados,
    'copiar_resultados':copiar_resultados,
    'excluir_resultados':excluir_resultados,
    'renomear_resultados':renomear_resultados,
}
