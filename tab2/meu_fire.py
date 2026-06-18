"""Implementação de mini-Fire."""

import sys
import inspect
import importlib.util
import re


# ---------------------------------------------------------------------------
# Utilitários de docstring
# ---------------------------------------------------------------------------

def _parse_docstring(doc: str):
    """
    Extrai descrição, descrições de parâmetros e retorno de uma docstring.
    Suporta formato mínimo e estilo Google.

    Retorna:
        (descricao_curta, dict[param -> descricao], retorno_str)
    """
    if not doc:
        return "", {}, ""

    linhas = doc.strip().splitlines()

    # Primeira linha não vazia = descrição curta
    descricao = ""
    for linha in linhas:
        stripped = linha.strip()
        if stripped:
            descricao = stripped
            break

    params = {}
    retorno = ""

    # Tenta parsear estilo Google (seções Args: e Returns:)
    secao_atual = None
    for linha in linhas:
        stripped = linha.strip()

        if re.match(r'^Args\s*:', stripped):
            secao_atual = "args"
            continue
        if re.match(r'^Returns?\s*:', stripped):
            secao_atual = "returns"
            continue
        # Nova seção desconhecida encerra o bloco
        if re.match(r'^\w[\w\s]*\s*:$', stripped) and stripped not in ("", ):
            if secao_atual in ("args", "returns"):
                secao_atual = None
            continue

        if secao_atual == "args":
            # Formato: "nome: descrição" (com indentação)
            m = re.match(r'^(\w+)\s*:\s*(.+)', stripped)
            if m:
                params[m.group(1)] = m.group(2).strip()

        elif secao_atual == "returns":
            if stripped:
                retorno = stripped

    # Fallback: formato mínimo — tenta extrair parâmetros da linha única
    # Ex: "Multiplica a por b. Parâmetros: a (int), b (int)."
    if not params:
        m = re.search(r'[Pp]ar[aâ]metros?\s*:\s*(.+)', descricao)
        if m:
            for item in m.group(1).split(","):
                item = item.strip().rstrip(".")
                pm = re.match(r'(\w+)\s*\(([^)]+)\)', item)
                if pm:
                    params[pm.group(1)] = f"({pm.group(2)})"

    return descricao, params, retorno


# ---------------------------------------------------------------------------
# Conversão de tipos
# ---------------------------------------------------------------------------

def _converter(valor: str, tipo):
    """Converte uma string para o tipo anotado na assinatura da função."""
    if tipo is bool or tipo is inspect.Parameter.empty and valor.lower() in (
        "true", "false", "yes", "no", "1", "0"
    ):
        return valor.lower() in ("true", "yes", "1")

    if tipo is int:
        try:
            return int(valor)
        except ValueError:
            raise ValueError(f"esperava int, recebeu {valor!r}")

    if tipo is float:
        try:
            return float(valor)
        except ValueError:
            raise ValueError(f"esperava float, recebeu {valor!r}")

    # str ou sem anotação: retorna como está
    return valor


# ---------------------------------------------------------------------------
# Carregamento do módulo
# ---------------------------------------------------------------------------

def _carregar_modulo(caminho: str):
    """Carrega dinamicamente um arquivo .py e retorna o módulo."""
    spec = importlib.util.spec_from_file_location("_modulo_dinamico", caminho)
    if spec is None:
        print(f"Erro: Arquivo '{caminho}' não encontrado")
        sys.exit(1)
    modulo = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(modulo)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho}' não encontrado")
        sys.exit(1)
    return modulo


def _coletar_funcoes(modulo) -> dict:
    """
    Retorna apenas as funções definidas no nível global do módulo
    (exclui funções importadas de outros módulos).
    """
    nome_modulo = modulo.__name__
    funcoes = {}
    for nome, obj in inspect.getmembers(modulo, inspect.isfunction):
        # Exclui funções importadas de outros módulos
        if obj.__module__ == nome_modulo:
            funcoes[nome] = obj
    return funcoes


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

def _exibir_help_geral(caminho: str, modulo, funcoes: dict):
    """Exibe o help geral do módulo listando todos os comandos."""
    nome_arquivo = caminho.split("/")[-1].split("\\")[-1]
    doc_modulo = inspect.getdoc(modulo) or ""

    print(f"Módulo: {nome_arquivo}")
    if doc_modulo:
        print(f"Descrição: {doc_modulo}")
    print()
    print("Comandos disponíveis:")

    for nome, func in funcoes.items():
        doc = inspect.getdoc(func) or ""
        descricao, param_docs, _ = _parse_docstring(doc)
        sig = inspect.signature(func)

        print(f"  {nome}  - {descricao}")
        print("  Parâmetros:")

        for pname, param in sig.parameters.items():
            tipo = param.annotation
            tipo_str = tipo.__name__ if tipo is not inspect.Parameter.empty else "str"
            tem_default = param.default is not inspect.Parameter.empty
            obrigatorio = not tem_default

            pdoc = param_docs.get(pname, "")

            if obrigatorio:
                info = f"--{pname} ({tipo_str}, obrigatório)"
            else:
                default = param.default
                # bool com padrão False → flag
                if tipo is bool:
                    info = f"--{pname} (bool, padrão={default})"
                else:
                    info = f"--{pname} ({tipo_str}, padrão={default!r})"

            if pdoc:
                print(f"      {info}: {pdoc}")
            else:
                print(f"      {info}")

        print()


def _exibir_help_comando(nome: str, func):
    """Exibe o help detalhado de um único comando."""
    doc = inspect.getdoc(func) or ""
    descricao, param_docs, retorno = _parse_docstring(doc)
    sig = inspect.signature(func)

    print(f"Comando: {nome}")
    print(f"Descrição: {descricao}")

    # Linha de uso
    partes_uso = [f"  {nome}"]
    positional_obrigatorios = []
    for pname, param in sig.parameters.items():
        tipo = param.annotation
        tipo_str = tipo.__name__.upper() if tipo is not inspect.Parameter.empty else "STR"
        tem_default = param.default is not inspect.Parameter.empty
        if tipo is bool:
            partes_uso.append(f"[--{pname}]")
        elif tem_default:
            partes_uso.append(f"[--{pname} {tipo_str}]")
        else:
            # Pode ser posicional obrigatório ou nomeado obrigatório
            positional_obrigatorios.append((pname, tipo_str))
            partes_uso.append(f"--{pname} {tipo_str}")

    print(f"\nUso: {' '.join(partes_uso)}")
    print("\nParâmetros:")

    for pname, param in sig.parameters.items():
        tipo = param.annotation
        tipo_str = tipo.__name__ if tipo is not inspect.Parameter.empty else "str"
        tem_default = param.default is not inspect.Parameter.empty
        pdoc = param_docs.get(pname, "")

        if not tem_default:
            linha = f"  --{pname} ({tipo_str}, obrigatório)"
        elif tipo is bool:
            linha = f"  --{pname} (bool, padrão={param.default})"
        else:
            linha = f"  --{pname} ({tipo_str}, padrão={param.default!r})"

        if pdoc:
            linha += f": {pdoc}"
        print(linha)

    if retorno:
        print(f"\nRetorna: {retorno}")


# ---------------------------------------------------------------------------
# Execução de comando
# ---------------------------------------------------------------------------

def _executar_comando(nome: str, func, args_cli: list):
    """Monta o parser para a função e a executa com os argumentos fornecidos."""
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""
    descricao, _, _ = _parse_docstring(doc)

    # Verifica --help específico do comando
    if "--help" in args_cli or "-h" in args_cli:
        _exibir_help_comando(nome, func)
        return

    # Separa argumentos posicionais dos nomeados (--chave valor)
    # Posicionais: valores sem prefixo "--" que aparecem antes de qualquer "--"
    positional_values = []
    i = 0
    while i < len(args_cli) and not args_cli[i].startswith("--"):
        positional_values.append(args_cli[i])
        i += 1
    named_args_raw = args_cli[i:]

    # Parseia --chave valor
    named = {}
    j = 0
    while j < len(named_args_raw):
        token = named_args_raw[j]
        if token.startswith("--"):
            chave = token[2:]
            # Verifica se é flag booleana (próximo token é outra flag ou não existe)
            if j + 1 >= len(named_args_raw) or named_args_raw[j + 1].startswith("--"):
                named[chave] = True
                j += 1
            else:
                named[chave] = named_args_raw[j + 1]
                j += 2
        else:
            j += 1

    # Monta os kwargs para a chamada
    kwargs = {}
    positional_idx = 0

    for pname, param in sig.parameters.items():
        tipo = param.annotation
        tem_default = param.default is not inspect.Parameter.empty

        if pname in named:
            raw = named[pname]
            # Flag booleana passada como --flag (sem valor)
            if raw is True:
                if tipo is bool:
                    # bool com padrão True → passar --flag significa False
                    if tem_default and param.default is True:
                        kwargs[pname] = False
                    else:
                        kwargs[pname] = True
                else:
                    kwargs[pname] = True
            else:
                try:
                    if tipo is not inspect.Parameter.empty:
                        kwargs[pname] = _converter(str(raw), tipo)
                    else:
                        kwargs[pname] = raw
                except ValueError as e:
                    print(f"Erro: Parâmetro '{pname}' {e}")
                    sys.exit(1)

        elif positional_idx < len(positional_values):
            # Argumento posicional obrigatório
            raw = positional_values[positional_idx]
            positional_idx += 1
            try:
                if tipo is not inspect.Parameter.empty:
                    kwargs[pname] = _converter(raw, tipo)
                else:
                    kwargs[pname] = raw
            except ValueError as e:
                print(f"Erro: Parâmetro '{pname}' {e}")
                sys.exit(1)

        elif tem_default:
            kwargs[pname] = param.default

        else:
            print(f"Erro: Função '{nome}' requer o argumento '{pname}'")
            sys.exit(1)

    # Executa
    func(**kwargs)


# ---------------------------------------------------------------------------
# Ponto de entrada principal
# ---------------------------------------------------------------------------

def meu_fire(caminho_modulo: str):
    """
    Ponto de entrada principal do mini-Fire.

    Carrega o módulo em caminho_modulo, descobre suas funções e
    interpreta sys.argv para despachar o comando correto.
    """
    modulo = _carregar_modulo(caminho_modulo)
    funcoes = _coletar_funcoes(modulo)

    # argv[0] = meu_fire.py, argv[1] = arquivo.py, argv[2:] = [comando] [args]
    resto = sys.argv[2:]

    # Sem comando ou --help geral
    if not resto or resto[0] in ("--help", "-h"):
        _exibir_help_geral(caminho_modulo, modulo, funcoes)
        return

    nome_comando = resto[0]
    args_cli = resto[1:]

    if nome_comando not in funcoes:
        print(f"Erro: Comando '{nome_comando}' não encontrado. Use --help para listar.")
        sys.exit(1)

    _executar_comando(nome_comando, funcoes[nome_comando], args_cli)


# ---------------------------------------------------------------------------
# Entrada via linha de comando
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 meu_fire.py <arquivo.py> [comando] [args...]")
        sys.exit(1)

    caminho = sys.argv[1]
    meu_fire(caminho)