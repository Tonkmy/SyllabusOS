# PROJECT OVERVIEW

这个仓库不是在线知识库产品，也不是需要持续运行的 agent 平台。

它是一个为本地高级 LLM 设计的知识型工作空间脚手架。  
同一个模型，在不同目录中打开时，应该进入不同角色，并按照该目录的文件协议工作。

项目的目标不是制造更多“隐藏记忆”，而是把状态、知识和工作边界放回文件系统里，让 ChatGPT、Codex、Claude、Opus 这类强模型在一个组织良好的环境中稳定发挥。

## 项目的本质

一句话概括：

**这是一个面向本地高级 LLM 的、双层 agent 驱动的 subject-based 工作空间协议。**

这里有三个关键词：

- `双层 agent`
  只有两个活跃 agent 层级：根目录教务处，以及具体工作空间里的执行 agent。
- `subject-based`
  `kind` 不再主要挂在 leaf 层，而是先挂在 `subject` 这一层。
- `文件协议`
  角色、状态、知识和工作边界都由目录与文件约定承载，而不是由一段超长 prompt 或一串聊天记录隐式承载。

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

- 管理 subject
- 管理 `kind`
- 决定一个新 subject 是 collection 还是 singleton
- 在 collection subject 下面新增课程或其他 child space
- 维护全局 registry
- 把用户路由到正确的目录

它不负责：

- 深度摄取具体空间的原始材料
- 在根目录直接进行知识生产
- 代替具体空间回答领域问题

根目录的价值，是提供秩序和脚手架，而不是承担一切工作。

### 2. Subject 层：kind 和 mode 的入口

现在的核心变化是：

**`kind` 前置到 `subject` 层。**

也就是说：

- `subjects/CSCI` 代表这是一个 `course` 型集合
- `subjects/HEALTH` 可以代表这是一个 `health_coach` 型顶层空间
- `subjects/INTERVIEW` 可以代表这是一个 `interview_coach` 型顶层空间

每个 subject 都有两个关键属性：

- `kind`
- `mode`

### 3. 两种 subject 形态

#### `collection`

subject 是容器，真正工作的 child space 直接挂在 subject 根目录下面。

例如：

```text
subjects/
  CSCI/
    subject.json
    INDEX.md
    ARIN5204 Reinforcement Learning/
    COMP7404 Machine Learning in Trading and Finance/
```

这最适合课程型学科。

#### `singleton`

subject 根目录本身就是 active space。

例如：

```text
subjects/
  HEALTH/
    subject.json
    CLAUDE.md
    PROFILE.md
    indexes/
    memory/
    notes/
    skills/
```

这最适合健康助手、面试助手、研究助手这类个人空间。

## 为什么这样更合理

之前把 `kind` 主要挂在 leaf workspace 上，虽然抽象上完整，但不够贴合实际使用。

你真正的使用心智其实是：

- `CSCI` 本身就表示“这里是一组课程”
- `Health` 本身就表示“这是一个健康教练空间”

也就是说，用户最先接触的，不是 leaf workspace 抽象，而是 `subject`。

把 `kind` 前置到 `subject` 层之后：

- 路径更短
- 用户更少接触抽象概念
- `CSCI` 这类课程集合和 `Health` 这类顶层空间都能自然表达
- 结构更接近你真正想要的使用方式

## 为什么仍然只保留双层 agent

这个项目仍然刻意保持双层活跃 agent，而不是继续增加“学科 agent”或更多中间角色。

原因很简单：

- 真正需要决策的，是结构管理和具体空间工作
- `collection` subject 只需要容器和索引，不需要独立人格
- `singleton` subject 已经是 active space 本身
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

### 2. Retrieval order matters more than bigger context

在这个项目里，模型效率主要来自正确的检索顺序，而不是更大的上下文窗口。

对于 active space，合理的读取顺序是：

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
  导航、source inventory、note inventory、space map
- `notes/chapters/*.md`
  经过沉淀后的稳定知识

### 4. Strong-model-friendly, not workflow-engine-friendly

这个项目默认用户会使用强模型。

所以它不追求把每一步都写成僵硬 SOP，而是提供：

- 清晰边界
- 最小必要流程
- 稳定文件角色
- 轻量护栏

模型应该在一个组织良好的环境中发挥理解力，而不是被过度规训成流程执行器。

### 5. Thin core, thick local customization

每个 active space 都分成三层：

- `CLAUDE.md`
  稳定内核，定义工作边界和主节奏
- `PROFILE.md`
  本地定制层，定义回答风格、目标、偏好、特殊规则
- `skills/`
  小而专门的能力模块，用来扩展空间的具体行为

这使得系统同时获得两种性质：

- 根目录和模板内核保持稳定
- 单个空间可以高度定制，而不污染全局

## 这个项目的亮点

### 亮点一：目录本身就是角色切换器

进入根目录，模型是教务处。  
进入 `subjects/CSCI/ARIN5204 Reinforcement Learning/`，模型就是这门课的 agent。  
进入 `subjects/HEALTH/`，模型就是健康助手。

不需要多余的模式切换按钮。

### 亮点二：subject 本身就表达了工作形态

`CSCI` 一眼就知道是课程集合。  
`HEALTH` 一眼就知道是顶层健康空间。

这个表达方式比 `subject/workspaces/...` 更贴近真实使用。

### 亮点三：Kinds 让系统既可复用又可生长

很多模板系统的问题是只有复用，没有生长；很多 agent 系统的问题是只有自由，没有稳定。

`kind` 现在绑定在 `subject` 层，刚好在两者之间提供了平衡：

- 先复用已有 kind
- 只有确实不适配时才新增 kind
- 一旦新 kind 成熟，后续同类 subject 就能沿用

### 亮点四：对高级模型友好

这个项目不是为弱模型补流程。

它假设模型本身已经足够强，因此重点放在：

- 提供清晰边界
- 降低树扫描成本
- 控制上下文噪音
- 保留本地定制空间

### 亮点五：把记忆从黑盒能力变成普通文件

项目不依赖神秘的“长期记忆”。

它把上下文恢复、导航、知识沉淀拆成普通文件：

- `workspace.json`
- `PROFILE.md`
- `indexes/INDEX.md`
- `memory/MEMORY.md`
- `notes/chapters/*.md`

这让系统更透明，也更容易长期维护。

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
  该 kind 的稳定 active-space 内核
- `templates/<kind>/PROFILE.md`
  该 kind 的本地定制入口
- `templates/<kind>/skills/`
  该 kind 的模块化行为层
- `scripts/scaffold.py`
  subject、kind、课程/空间脚手架和索引同步
- `scripts/audit.py`
  结构与状态的一致性审计
- `scripts/md_to_pdf.py`
  Markdown 笔记的 PDF 导出
- `scripts/pdf_to_text.py`
  PDF 提取辅助工具

## 它不打算成为什么

这个项目当前不打算做：

- 在线 SaaS 知识库
- 多用户协同平台
- 数据库驱动的复杂知识中台
- 多层 agent 编排系统
- 每个课程集合再挂一个独立学科 agent
- 多套并行 note 体系
- 把聊天记录本身当成长期状态存储

它的重心始终是：

**本地目录 + 文件协议 + 强模型 + 可维护的知识沉淀。**

## 长期方向

如果继续发展，这个项目最值得强化的方向不是“加更多功能”，而是继续让协议更稳、结构更清、定制更自然。

值得继续强化的方向包括：

- 更稳的命名与索引规则
- 更成熟的 kind 模板库
- 更清晰的 `collection / singleton` 使用边界
- 更可靠的 audit 建议
- 更高质量的 space-level customization

## 总结

这个项目真正有价值的地方，不在于用了多少“最新 agent 术语”，而在于它抓住了一个更根本的问题：

**当模型已经很强之后，决定表现上限的，往往不是再造一个更复杂的系统，而是能否给模型一个组织良好的工作空间。**

这个仓库的回答是：

- 用目录承载角色
- 用文件承载状态
- 用 `subject.kind + subject.mode` 承载结构语义
- 用索引降低上下文成本
- 用笔记承载稳定知识
- 用 `PROFILE.md` 和 `skills/` 释放本地定制能力

它不是一个“会自动完成一切”的平台。

它是一套更朴素、也更可持续的方法：

**如何为本地高级 LLM 设计一个长期可工作的知识型工作空间。**
