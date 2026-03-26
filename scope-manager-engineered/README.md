# Scope Manager Evoluído — Projetos Engenheirados de Máquinas Elétricas Girantes

Este diretório contém os artefatos de modelagem para o módulo de **Gerenciamento de Projetos Engenheirados** do Scope Manager, conforme a recomendação das **Opções 1 + 4** da análise técnica.

---

## Arquivos

| Arquivo | Tipo | Finalidade |
|---|---|---|
| `engineered-project-flow.bpmn` | BPMN 2.0 (Camunda 8) | Processo completo do fluxo engenheirado com lanes, gateways, timers e service tasks |
| `architecture-diagram.drawio` | Draw.io (mxGraph XML) | Diagrama de arquitetura da solução completa: fluxo padrão, módulo engenheirado e orquestração |
| `README.md` | Markdown | Esta documentação |

---

## Como abrir o arquivo BPMN no Camunda Modeler

1. Faça o download do **Camunda Modeler** em: https://camunda.com/download/modeler/
2. Abra o Camunda Modeler.
3. Vá em **File → Open File…** e selecione `engineered-project-flow.bpmn`.
4. O diagrama será carregado com todas as lanes, tarefas, gateways e boundary events.
5. Para fazer o deploy no Camunda Engine, use **Deploy Current Diagram** (ícone de nuvem).

> **Nota:** O arquivo é compatível com **Camunda 8** (namespace `http://camunda.org/schema/1.0/bpmn`).

---

## Como abrir o diagrama Draw.io

1. Acesse https://app.diagrams.net no navegador.
2. Clique em **Open Existing Diagram** (ou arraste o arquivo para a janela).
3. Selecione `architecture-diagram.drawio` no seu computador.
4. O diagrama será exibido com três seções coloridas: laranja (fluxo padrão), azul (módulo engenheirado) e roxo (orquestração).

---

## Entidades Principais

### `EngineeringProject`
Entidade de primeiro nível do módulo engenheirado. Agrega todas as informações de um projeto fora do padrão.

| Campo | Descrição |
|---|---|
| `cliente` | Nome do cliente solicitante |
| `descricao` | Descrição técnica do projeto |
| `prazo` | Data limite esperada |
| `tipo` | `ENGINEERED` ou `SEMI-ENGINEERED` |
| `status` | `DRAFT` → `TECHNICAL_REVIEW` → `COMMERCIAL_REVIEW` → `APPROVED` → `RELEASED` |

---

### `Anchor Product`
Referência a um produto existente no **Collection ElectricalSystem** do fluxo padrão do Scope Manager. Serve como base técnica para o projeto engenheirado.

- Buscado via o componente **Finder** existente.
- Define o ponto de partida: especificações, BOM e escopo padrão.
- Todos os desvios são registrados **relativos ao âncora**.

---

### `DeviationRegister`
Lista de todos os itens que diferem do produto âncora.

| Campo | Descrição |
|---|---|
| `item` | Campo ou componente modificado |
| `specCustomizada` | Especificação técnica customizada para este projeto |
| `impactoBOM` | Impacto na lista de materiais (BOM) |
| `justificativaTecnica` | Obrigatória quando o desvio é classificado como crítico |

---

### `ApprovalGates`
Workflow de aprovação em duas etapas para garantir rastreabilidade e controle de qualidade.

| Gate | Responsável | Critério |
|---|---|---|
| **Gate 1 — Technical Review** | Engenheiro Elétrico → Aprovador de Engenharia | Consistência técnica dos desvios e da solução proposta |
| **Gate 2 — Commercial Review** | Solicitante Comercial → Aprovador Comercial | Viabilidade comercial, prazo e margem da cotação |

> Ambos os gates possuem **timeout de 5 dias** (boundary timer event no BPMN). Se expirar sem aprovação, o processo retorna para revisão automática.

---

### `ScopeConsolidation`
Etapa automática (Service Task) que gera o escopo final consolidado.

```
Escopo Final = Produto Âncora + Desvios Aprovados
Status Final = LIBERADO PARA COTAÇÃO
```

O output é utilizado pelo solicitante para enviar a cotação ao cliente.

---

## Tabela Comparativa: Produto Padrão vs Projeto Engenheirado

| Característica | Produto Padrão (Standard) | Projeto Engenheirado |
|---|---|---|
| **Escopo** | Fixo / configurável por plataforma | Variável / customizado por projeto |
| **Hierarquia** | Rígida: Configuration → Platform → Product → Commercial → ElectricalPlatform → ElectricalProject → Collection | Flexível: EngineeringProject → Anchor + Desvios |
| **Rastreabilidade** | Por plataforma / produto | Por projeto / cliente |
| **Ciclo de vida** | Cotação → Pedido | Requisito → Engenharia → Cotação → Aprovação → Liberação |
| **Reuso** | Alto (templates fixos) | Médio (âncora + delta de desvios) |
| **Aprovações** | Automáticas (fluxo configurado) | Manuais por etapa (Gate 1 + Gate 2) |
| **BOM** | Derivada da plataforma padrão | BOM do âncora + impacto de cada desvio |
| **Ferramenta de busca** | Finder no Collection ElectricalSystem | Finder (reaproveitado) para buscar âncoras |
| **Entidade principal** | `ElectricalProject` | `EngineeringProject` |
| **Desvios** | Não suportado | `DeviationRegister` com rastreabilidade completa |
| **Timers de aprovação** | N/A | 5 dias por gate (boundary timer event) |

---

## Visão Geral do Fluxo BPMN

```
[Solicitante Comercial]
  START → Criar EngineeringProject → Selecionar Anchor Product

[Engenheiro Elétrico]
  → Capturar Requisitos Técnicos → Registrar Deviation List
  → [Gateway] Desvios críticos?
       SIM → Documentar Justificativa Técnica
       NÃO → (segue)

[Sistema — Scope Manager]
  → Consolidar Scope (Âncora + Desvios) [Service Task automático]

[Aprovador de Engenharia]
  → Revisar Escopo Técnico (Gate 1)
  → [Gateway] Aprovado pela Engenharia?
       REJEITADO → Engenheiro revisa desvios (loop)
       APROVADO → (segue)

[Aprovador Comercial]
  → Revisar Cotação e Escopo Consolidado (Gate 2)
  → [Gateway] Aprovado Comercialmente?
       REJEITADO → Solicitante revisa requisitos (loop)
       APROVADO → (segue)

[Sistema — Scope Manager]
  → Gerar Output de Cotação [Service Task automático]

[Solicitante Comercial]
  → Enviar Cotação ao Cliente → END
```

---

## Referências

- Camunda BPMN 2.0: https://docs.camunda.org/manual/latest/reference/bpmn20/
- Draw.io (app.diagrams.net): https://app.diagrams.net
- Camunda Modeler: https://camunda.com/download/modeler/
