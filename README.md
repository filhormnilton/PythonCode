# Orchestra Tool

Ferramenta CLI para gerenciamento de configurações via APIs do Orchestra (WEG).

## Estrutura

```
orchestra_tool/
├── api/             # Clientes HTTP (Model API, Function API)
├── models/          # Dataclasses de resultado
├── services/        # Regras de negócio (clone, update, fert_link, compare)
└── utils/           # Helpers (excel_writer, constraint_parser, operation_processor)
main.py              # Entry point com argparse
```

## Configuração via variáveis de ambiente

| Variável           | Padrão                 | Descrição                    |
|--------------------|------------------------|------------------------------|
| `ORCHESTRA_ENV`    | `beta`                 | `beta` ou `prd`              |
| `MODEL_URL`        | URL interna beta       | Override direto da URL       |
| `FUNCTION_API_URL` | URL interna beta       | Override direto da URL       |
| `OUTPUT_DIR`       | `C:/Users/niltonf/dev` | Diretório de entrada e saída |
| `VERIFY_SSL`       | `false`                | `true` para habilitar SSL    |

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py --mode operations
python main.py --mode fert_link
python main.py --mode compare
python main.py --mode all
```
