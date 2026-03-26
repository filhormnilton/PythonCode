# Orchestra Tool

Ferramenta CLI para gerenciamento de configurações via APIs do Orchestra (WEG).

---

## 📁 Estrutura do Repositório

```
PythonCode/
├── Poc/                     # ← Pasta Poc (ver abaixo)
│   ├── README.md
│   ├── architecture-diagram.drawio
│   └── engineered-project-flow.bpmn
├── orchestra_tool/
│   ├── api/
│   ├── models/
│   ├── services/
│   └── utils/
├── main.py
└── requirements.txt
```

## 📂 Pasta Poc — Scope Manager Evoluído

> A pasta **[`Poc/`](./Poc/)** contém os artefatos de modelagem para o módulo de **Projetos Engenheirados de Máquinas Elétricas Girantes**.

| Arquivo | Visualizar Online |
|---|---|
| `architecture-diagram.drawio` | **[▶ Abrir no diagrams.net](https://app.diagrams.net/#Uhttps://raw.githubusercontent.com/filhormnilton/PythonCode/main/Poc/architecture-diagram.drawio)** |
| `engineered-project-flow.bpmn` | **[▶ Abrir no bpmn.io](https://demo.bpmn.io/)** (arraste o arquivo) |
| `README.md` (documentação completa) | **[📄 Ver documentação](./Poc/README.md)** |

---

## Estrutura do `orchestra_tool`

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
