# Poc — Scope Manager Evoluído: Projetos Engenheirados de Máquinas Elétricas Girantes

Esta pasta contém os artefatos de modelagem para a solução recomendada de **Gerenciamento de Projetos Engenheirados de Máquinas Elétricas Girantes** (Scope Manager Evoluído — Opções 1 + 4).

---

## Arquivos

| Arquivo | Descrição | Como Abrir |
|---|---|---|
| `engineered-project-flow.bpmn` | Processo BPMN 2.0 completo do fluxo engenheirado, com 5 swim lanes, gateways, boundary timers e service tasks | **[Camunda Modeler](https://camunda.com/download/modeler/)** (v5+) |
| `architecture-diagram.drawio` | Diagrama de arquitetura com as 3 seções da solução: Fluxo Padrão, Módulo Engenheirado e Orquestração API | **[app.diagrams.net](https://app.diagrams.net)** ou Extensão VS Code Draw.io |

---

## Como Abrir os Arquivos

### `engineered-project-flow.bpmn`
1. Baixe e instale o **[Camunda Modeler](https://camunda.com/download/modeler/)** (versão 5 ou superior)
2. Abra o Camunda Modeler
3. Clique em **File → Open File…** e selecione `engineered-project-flow.bpmn`
4. O processo será exibido com todas as lanes, tarefas, gateways e eventos

### `architecture-diagram.drawio`
1. Acesse **[app.diagrams.net](https://app.diagrams.net)** no navegador
2. Clique em **File → Open From → Device** e selecione `architecture-diagram.drawio`
3. Ou instale a extensão **Draw.io** no VS Code e abra o arquivo diretamente

---

## Comparativo: Produto Padrão vs Projeto Engenheirado

| Dimensão | Produto Padrão (atual) | Projeto Engenheirado (novo) |
|---|---|---|
| **Escopo** | Fixo / configurável por hierarquia | Variável / customizado por projeto |
| **Hierarquia** | Rígida: `Configuration → Platform → Product → Commercial → ElectricalPlatform → ElectricalProject → Collection` | Flexível: `EngineeringProject → AnchorProduct + DeviationRegister + ApprovalGates → ScopeConsolidation` |
| **Rastreabilidade** | Por plataforma e produto | Por projeto e cliente, com rastreio de cada desvio |
| **Ciclo de Vida** | Cotação → Pedido | Requisito → Engenharia → Aprovação Técnica → Aprovação Comercial → Cotação |
| **Reuso** | Alto (templates rígidos) | Médio (produto âncora + delta de desvios) |
| **Aprovações** | Automáticas (fluxo padrão) | Manuais por etapa: Gate 1 (Técnico) e Gate 2 (Comercial), com timeout de 5 dias |

---

## Entidades do Módulo Engenheirado

### `EngineeringProject`
Entidade de primeiro nível que representa um projeto engenheirado. Contém:
- `cliente` — identificação do cliente
- `descricao` — descrição do projeto
- `prazo` — data limite
- `tipo` — `ENGINEERED` ou `SEMI-ENGINEERED`
- `status` — `DRAFT | TECHNICAL_REVIEW | COMMERCIAL_REVIEW | LIBERADO_PARA_COTACAO`

### `AnchorProduct`
Referência a um produto existente no fluxo padrão do Scope Manager (obtido via Finder na `Collection ElectricalSystem`). Serve como base para o escopo engenheirado. Todos os desvios são registrados em relação a este produto âncora.

### `DeviationRegister`
Lista de desvios em relação ao produto âncora. Cada desvio contém:
- `campo` — campo ou especificação que diverge
- `spec` — especificação customizada para este projeto
- `bom_impact` — impacto na lista de materiais (BOM)
- `justificativa_tecnica` — obrigatório para desvios críticos

### `ApprovalGates`
Workflow de aprovação em duas etapas:
- **Gate 1 — Technical Review:** Revisão pelo Aprovador de Engenharia. Timeout de 5 dias gera notificação de reescalonamento.
- **Gate 2 — Commercial Review:** Revisão pelo Aprovador Comercial. Timeout de 5 dias gera notificação de reescalonamento.
- Em caso de rejeição no Gate 1, o Engenheiro revisa os desvios.
- Em caso de rejeição no Gate 2, o Solicitante revisa os requisitos.

### `ScopeConsolidation`
Output final do processo engenheirado:
- Consolida automaticamente: **Produto Âncora + Lista de Desvios aprovados**
- Gera status `LIBERADO_PARA_COTACAO`
- Alimenta o processo de cotação ao cliente

---

## Processo BPMN — Swim Lanes

| Lane | Responsabilidade |
|---|---|
| **Solicitante Comercial** | Inicia o projeto, seleciona âncora, revisa requisitos (se rejeitado), envia cotação ao cliente |
| **Engenheiro Elétrico** | Captura requisitos técnicos, registra desvios, documenta justificativas técnicas, revisa desvios (se rejeitado) |
| **Aprovador de Engenharia** | Aprova ou rejeita o escopo técnico consolidado (Gate 1) |
| **Aprovador Comercial** | Aprova ou rejeita a cotação e escopo consolidado (Gate 2) |
| **Sistema (Scope Manager)** | Verifica existência de desvios críticos, consolida o escopo (Âncora + Desvios), gera output de cotação |

---

## Nota de Compatibilidade

### BPMN — Camunda 7 (namespace atual)
O arquivo `engineered-project-flow.bpmn` usa o namespace **Camunda Platform 7**:
```xml
xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
```

### Migração para Camunda 8 / Zeebe
Para migrar para **Camunda 8 (Zeebe)**, as seguintes alterações são necessárias:
- Substituir `xmlns:camunda` por `xmlns:zeebe="http://camunda.org/schema/zeebe/1.0"`
- Substituir `camunda:assignee` por `zeebe:assignmentDefinition assignee="..."` dentro de `<extensionElements>`
- Substituir `camunda:expression` em Service Tasks por `zeebe:taskDefinition type="..."` com workers Zeebe
- Substituir `camunda:formData` por `zeebe:userTaskForm` ou formulários Camunda Forms
- Revisar `camunda:candidateGroups` para o formato Zeebe equivalente
- Usar a ferramenta **[Camunda Modeler Migration Assistant](https://docs.camunda.io/docs/guides/migrating-from-camunda-7/)** para automatizar parte da migração
