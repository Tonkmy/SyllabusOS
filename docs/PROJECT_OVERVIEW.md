# PROJECT OVERVIEW

这个仓库不是在线知识库产品，也不是需要持续运行的 agent 平台。

它是一个为本地高级 LLM 设计的工作空间脚手架。  
同一个模型，在不同目录中打开时，应该进入不同角色，并按照该目录的文件协议工作。

项目的目标不是制造更多“隐藏记忆”，而是把状态、知识和工作边界放回文件系统里，让 ChatGPT、Codex、Claude、Opus 这类强模型在一个组织良好的环境中稳定发挥。

## 项目的本质

一句话概括：

**这是一个面向本地高级 LLM 的、双层 agent 驱动的知识型工作空间协议。**

这里有三个关键词：

- `双层 agent`
  只有两个活跃 agent 层级：根目录的教务处，以及叶子 workspace 中的执行 agent。
- `文件协议`
  角色、状态、知识和工作边界都由目录与文件约定承载，而不是由一段超长 prompt 或一串聊天记录隐式承载。
- `本地工作空间`
  核心运行形态是文件夹、索引、笔记、模板和脚本，不依赖在线编排平台。

## 它解决的核心问题

很多知识仓库最终会失控，常见原因不是模型不够强，而是环境设计不适合模型长期工作：

- 根目录助手反复扫全仓
- 原始 PDF 和笔记混在一起
- 会话历史承担了本该由文件承担的状态职责
- 每次进入目录，模型都像第一次见到这个项目
- 用户不知道该在什么目录里让模型做什么事

这个项目的解决方式很直接：

- 用目录切换角色
- 用小而清晰的状态文件恢复上下文
- 用索引降低树扫描成本
- 用章节笔记承载稳定知识
- 用轻脚本守住结构一致性

它关注的不是“让模型更会记”，而是“让模型更容易在正确的地方做正确的事”。

## 当前架构

### 1. 根目录：Registrar

根目录的 `CLAUDE.md` 定义了一个稳定的教务处 agent。

它负责：

- 管理学科
- 管理 leaf workspace
- 管理 `kind`
- 维护全局 registry
- 把用户路由到正确的 workspace

它不负责：

- 深度摄取具体 workspace 的原始材料
- 在根目录直接进行知识生产
- 代替某个 workspace 回答具体领域问题

根目录的价值，是提供秩序和脚手架，而不是承担一切工作。

### 2. 学科目录：Passive Container

学科目录不是第三层 agent。

它只是被动容器，用来提供 namespace 和中间导航层，减少根目录与叶子 workspace 的直接混乱。

它保留：

- `subject.json`
- `INDEX.md`
- `workspaces/`

这已经足够，不需要赋予它独立人格。

### 3. 叶子目录：Kind-based Workspace Agent

真正做知识工作的，是叶子 workspace。

这里不再被硬编码成“课程目录”。  
`course` 只是默认的第一个 `kind`，适合 lecture-driven 的学术课程；未来也可以有 `health_coach`、`interview_prep`、`research_assistant` 等其他 kind。

也就是说，这个项目真正支持的是：

- 根目录有一个稳定的 registrar
- 每个叶子目录都有一个可定制的 workspace agent
- `course` 只是其中一种常用 workspace 形态

## 为什么引入 Kind

如果叶子目录永远只有课程一种形态，那么系统很快会遇到边界问题。

例如：

- 健康知识助手并不是一门课
- 面试准备空间也不完全等同于课程
- 某些项目型工作空间需要不同的知识沉淀方式

因此，项目把叶子目录抽象为 `workspace`，再用 `kind` 来描述它的结构和行为模板。

根目录 agent 的工作逻辑变成：

1. 接收用户的新 workspace 需求
2. 查看 `templates/INDEX.md`
3. 如果已有匹配 kind，直接使用
4. 如果没有匹配 kind，创建新 kind
5. 用选定 kind 初始化 leaf workspace

这样做有两个好处：

- 复用已有结构，避免每次从零设计
- 保留自由度，让系统可以自然长出新的 workspace 形态

## 为什么是双层，而不是多层 agent

这个项目刻意保持双层活跃 agent，而不是继续增加“学科 agent”或更多中间角色。

原因很简单：

- 真正需要决策的，是结构管理和叶子工作
- 学科目录只需要容器和索引，不需要独立人格
- 层级越多，职责越容易模糊
- 对强模型来说，清边界比多流程更重要

这个仓库不是为了构建复杂 agent 编排图，而是为了给强模型一个轻量、稳定、低摩擦的工作环境。

## 设计原则

### 1. File-first, not chat-first

重要状态应该写回文件，而不是依附在会话里。

典型状态层包括：

- `registry/catalog.json`
- `registry/INDEX.md`
- `templates/INDEX.md`
- `templates/<kind>/kind.json`
- `subjects/<subject>/subject.json`
- `subjects/<subject>/INDEX.md`
- `workspace.json`
- `indexes/INDEX.md`
- `memory/MEMORY.md`
- `notes/chapters/*.md`

这样做的意义是：

- 状态可见
- 状态可审计
- 状态可迁移
- 状态可被不同模型共享

这里还有一个重要边界：

- 结构变化和知识变化应该写回文件
- 普通问答默认停留在当前会话，不自动落盘

这样可以避免把每次对话都错误地升级成长期状态。

### 2. Retrieval order matters more than bigger context

在这个项目里，模型效率主要来自正确的检索顺序，而不是更大的上下文窗口。

对于 leaf workspace，合理的读取顺序是：

1. `workspace.json`
2. `PROFILE.md`
3. `indexes/INDEX.md`
4. `memory/MEMORY.md`
5. 当前任务相关的 `skills/*.md`
6. 最小相关集合的 `notes/chapters/*.md`
7. 必要时才读 `materials/`

这是一种明确的 context engineering：  
先读高信号状态，再读导航层，再读稳定知识，最后才接触高噪音原始材料。

### 3. Keep memory small, keep knowledge in notes

`MEMORY.md` 不是第二知识库。

在这个项目里，三层职责是清楚分开的：

- `memory/MEMORY.md`
  短缓存、待办、提醒、现场恢复
- `indexes/INDEX.md`
  导航、source inventory、note inventory、course map 或 workspace map
- `notes/chapters/*.md`
  经过沉淀后的稳定知识

如果这三层混在一起，仓库会很快失控。

### 4. Strong-model-friendly, not workflow-engine-friendly

这个项目默认用户会使用强模型。

所以它不追求把每一步都写成僵硬 SOP，而是提供：

- 清晰边界
- 最小必要流程
- 稳定文件角色
- 轻量护栏

模型应该在一个组织良好的环境中发挥理解力，而不是被过度规训成流程执行器。

### 5. Thin core, thick local customization

这是当前版本非常重要的一条原则。

每个 leaf workspace 都分成三层：

- `CLAUDE.md`
  稳定内核，定义工作边界和主节奏
- `PROFILE.md`
  本地定制层，定义回答风格、目标、偏好、特殊规则
- `skills/`
  小而专门的能力模块，用来扩展 workspace 的具体行为

这使得系统同时获得两种性质：

- 根目录和模板内核保持稳定
- 单个 workspace 可以高度定制，而不污染全局

## Workspace 的标准工作方式

一个典型 workspace 的主节奏大致是：

1. `intake`
   接收新材料，整理到 `materials/` 下的合适位置
2. `index`
   更新 `indexes/INDEX.md`，维护 source 和 note 的可见性
3. `synthesize`
   把原始材料沉淀成 `notes/chapters/*.md`
4. `ask`
   优先基于已沉淀的 notes 回答问题，必要时再补读 source
5. `audit`
   检查结构和状态是否仍然一致

这里真正重要的，不是“多回答几次问题”，而是持续把知识推向稳定层。

理想状态下：

- `materials/` 是来源层
- `indexes/INDEX.md` 是导航层
- `notes/chapters/` 是主知识层
- `memory/MEMORY.md` 始终保持短小

普通 `ask` 不要求默认写回文件。  
只有当问题暴露出覆盖缺口，或用户明确要求沉淀结果时，workspace 才应更新索引、记忆或笔记。

## 定制化能力是项目亮点，不是例外

这个仓库并不要求所有 leaf workspace 都长得一样。

相反，它明确支持两类定制：

### 1. Workspace-level 定制

同一个 kind 下，不同 workspace 可以通过 `PROFILE.md` 和 `skills/` 呈现不同风格。

例如：

- 一个课程 workspace 更偏严谨推导
- 另一个课程 workspace 更偏 exam prep
- 某个 workspace 强调双语回答
- 某个 workspace 增加特定的分析流程或输出格式

### 2. Kind-level 定制

当用户的需求明显超出现有 kind 时，root registrar 可以新建 kind，并让后续同类 workspace 复用它。

例如：

- `course`
  lecture-driven academic workspace
- `health_coach`
  健康饮食与生活习惯教练
- `interview_prep`
  面试问答、题库、岗位定制复盘空间

这意味着项目不是“课程模板集合”，而是“可长出新 workspace 物种的本地 agent 工作空间”。

## 这个项目的亮点

### 亮点一：角色切换由目录触发

用户不需要在一个巨型系统里手动切换模式。  
进入根目录，模型就是教务处；进入 leaf workspace，模型就是该 workspace 的执行 agent。

目录本身就是角色切换器。

### 亮点二：仓库结构本身就是 prompt 的一部分

这个项目的 prompt 不只写在 `CLAUDE.md` 里。

真正共同约束模型行为的，还包括：

- 目录层级
- 文件命名
- 状态文件位置
- 索引结构
- note 组织方式
- kind 模板的边界

也就是说，工程结构本身就是隐性的 prompt 设计。

### 亮点三：把记忆从黑盒能力变成普通文件

项目不依赖神秘的“长期记忆”。

它把上下文恢复、导航、知识沉淀拆成普通文件：

- `workspace.json`
- `PROFILE.md`
- `indexes/INDEX.md`
- `memory/MEMORY.md`
- `notes/chapters/*.md`

这让系统更透明，也更容易长期维护。

### 亮点四：对高级模型友好

这个项目不是为弱模型补流程。

它假设模型本身已经足够强，因此重点放在：

- 提供清晰边界
- 降低树扫描成本
- 控制上下文噪音
- 保留本地定制空间

这比继续堆叠重型 agent runtime 更适合本地强模型协作。

### 亮点五：Kinds 让系统既可复用又可生长

很多模板系统的问题是只有复用，没有生长；很多 agent 系统的问题是只有自由，没有稳定。

`kind` 恰好在两者之间提供了平衡：

- 先复用已有 kind
- 只有确实不适配时才新增 kind
- 一旦新 kind 成熟，后续同类 workspace 就能沿用

这让项目在不变复杂的前提下具备演化能力。

## 当前仓库里最关键的实现

当前版本的核心能力已经体现在以下文件中：

- `CLAUDE.md`
  根目录 registrar 协议
- `registry/catalog.json`
  全局 machine-readable registry
- `registry/INDEX.md`
  全局 human-readable 索引
- `templates/INDEX.md`
  当前可用 kind 的总览
- `templates/<kind>/kind.json`
  kind 的机器可读定义
- `templates/<kind>/CLAUDE.md`
  该 kind 的稳定 workspace 内核
- `templates/<kind>/PROFILE.md`
  该 kind 的本地定制入口
- `templates/<kind>/skills/`
  该 kind 的模块化行为层
- `scripts/scaffold.py`
  学科、kind、workspace 的脚手架和索引同步
- `scripts/audit.py`
  结构与状态的一致性审计
- `scripts/md_to_pdf.py`
  Markdown 笔记的 PDF 导出
- `scripts/pdf_to_text.py`
  PDF 提取辅助工具

这些组件共同构成了当前版本的最小可用核心。

其中 `audit` 的定位也很明确：

- 它是轻量体检和修复建议工具
- 它默认给 repair checklist
- 它不应在未经确认的情况下自动重写整个 workspace

## 它不打算成为什么

为了防止方向漂移，也需要明确边界。

这个项目当前不打算做：

- 在线 SaaS 知识库
- 多用户协同平台
- 数据库驱动的复杂知识中台
- 多层 agent 编排系统
- 每个学科一个活跃 agent
- 多套并行 note 体系
- 把聊天记录本身当成长期状态存储

它的重心始终是：

**本地目录 + 文件协议 + 强模型 + 可维护的知识沉淀。**

## 长期方向

如果继续发展，这个项目最值得强化的方向不是“加更多功能”，而是继续让协议更稳、结构更清、定制更自然。

值得继续强化的方向包括：

- 更稳的命名与索引规则
- 更成熟的 kind 模板库
- 更清晰的 `skills/` 拆分
- 更可靠的 audit 建议
- 更高质量的 workspace-level customization

未来当然可以接入外部资料源、MCP 或更多工具，但这些都应该是输入增强层，而不是替代这个项目核心方法的主角。

## 总结

这个项目真正有价值的地方，不在于用了多少“最新 agent 术语”，而在于它抓住了一个更根本的问题：

**当模型已经很强之后，决定表现上限的，往往不是再造一个更复杂的系统，而是能否给模型一个组织良好的工作空间。**

这个仓库的回答是：

- 用目录承载角色
- 用文件承载状态
- 用索引降低上下文成本
- 用笔记承载稳定知识
- 用 `kind` 承载可复用的 workspace 形态
- 用 `PROFILE.md` 和 `skills/` 释放本地定制能力

它不是一个“会自动完成一切”的平台。

它是一套更朴素、也更可持续的方法：

**如何为本地高级 LLM 设计一个长期可工作的知识型 workspace。**
