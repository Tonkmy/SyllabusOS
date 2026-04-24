# Agent KB Template

我做这个仓库，是因为我不想每次开新对话都重新给模型讲背景，也不想把一堆 lecture notes 反复塞进上下文。

所以我把它做成了一个很朴素的东西：

- 在根目录打开 Claude / Codex / ChatGPT，它就是教务处
- 进入某个 workspace 再打开，它就是这个 workspace 的专属 agent
- 资料放进文件夹，知识沉淀回笔记，状态尽量留在仓库里

这不是网站，不是 SaaS，也不是那种要搭一堆服务才能跑的项目。  
它就是一个给个人使用的本地 agent 工作空间模板。

如果你想看完整设计思路、方法论和长期设想，直接看 [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)。  
这份 README 只负责一件事：让你尽快用起来。

## 这个项目能干嘛

最适合下面这类场景：

- 课程学习
- lecture notes 整理
- 按章节沉淀 Markdown 笔记
- 让 agent 在课程语境里回答问题
- 做非课程类的个人 workspace，比如健康助手、面试准备、项目研究空间

## 你只要记住这套用法

### 1. 在根目录打开 agent

根目录的 agent 是教务处，负责：

- 新建学科
- 新建 workspace
- 选择已有 `kind`
- 没有合适 `kind` 时新建一个

你可以直接跟它说人话，比如：

- “帮我新建一个 CSCI 学科”
- “在 CSCI 下面加一门 Reinforcement Learning”
- “我想建一个健康饮食教练 workspace，看看有没有合适 kind，没有就新建一个”

### 2. 进入目标 workspace 再打开 agent

到了 workspace 目录后，这个 agent 才开始干具体活。

常见动作就是：

- 看资料
- 整理资料
- 更新索引
- 写章节笔记
- 回答问题
- 导出 PDF

### 3. 新资料直接丢进去

默认放这里：

```text
materials/inbox/
```

如果你自己已经分好了，也可以直接放进：

- `materials/lectures/`
- `materials/assignments/`
- `materials/references/`

然后直接告诉 agent：

- “我刚刚把新 lecture 放进 `materials/lectures/` 了，你帮我 review 一下并更新索引”
- “`materials/references/` 里新增了一份 paper，你看看它该归到哪里”

不用太担心流程卡得很死。  
这个仓库本来就是给强模型用的，很多时候你只要把文件放对位置，再把情况说清楚，它自己就能接住。

### 4. 问问题就在 workspace 里问

平时问答不要在根目录问。  
根目录只做管理；真正回答内容问题的，是 leaf workspace 里的 agent。

## 最快上手

### 最低配置

如果你只想先试试脚手架和审计，`Python 3` 就够了：

```bash
python3 scripts/scaffold.py list-kinds
python3 scripts/audit.py .
```

### 完整配置

如果你还想用 PDF 导出和文本提取工具，再装依赖：

```bash
uv sync
```

### 直接跑一遍

1. 新建学科

```bash
uv run python scripts/scaffold.py add-subject CSCI "Computer Science"
```

2. 新建一个标准课程 workspace

```bash
uv run python scripts/scaffold.py add-course CSCI ARIN5204 "Reinforcement Learning"
```

3. 或者显式指定 kind

```bash
uv run python scripts/scaffold.py add-workspace CSCI RL "Reinforcement Learning" --kind course
```

4. 如果没有合适 kind，就先克隆一个新的 kind 再用

```bash
uv run python scripts/scaffold.py add-kind health_coach --name "Health Coach" --description "Leaf workspace for health coaching" --from-kind course
uv run python scripts/scaffold.py add-workspace HEALTH COACH "Health Coach" --kind health_coach
```

## 日常怎么用

一个很顺手的节奏通常是这样：

1. 在根目录让教务处 agent 帮你建好 workspace
2. 进入对应 workspace
3. 把资料丢进 `materials/inbox/`
4. 让 agent 做 intake / index / chapter
5. 之后所有课程问题都在这个 workspace 里问
6. 需要导出时再转 PDF

我自己的建议是：  
仓库下载下来之后，先直接让你的 agent 对整个仓库做一次 review。

比如你可以在根目录说：

- “你先 review 一下这个仓库，告诉我该怎么开始用”
- “按你的理解，带我走一遍最适合新手的使用流程”

这类项目本来就是给 LLM 用的，所以最好的说明员，很多时候就是它自己。

## 目录不用全懂，先认识这几个就够了

### 根目录

- `CLAUDE.md`
  教务处 agent 的灵魂文件
- `registry/catalog.json`
  全局 registry
- `templates/INDEX.md`
  当前有哪些 kind

### 每个 workspace

- `CLAUDE.md`
  这个 workspace 的稳定内核
- `PROFILE.md`
  这个 workspace 的本地定制
- `skills/`
  这个 workspace 的附加能力
- `indexes/INDEX.md`
  source 和 note 的索引表
- `memory/MEMORY.md`
  短缓存，不是知识库正文
- `notes/chapters/`
  真正常驻的知识层

## 想定制的话，改哪里

我建议按这个顺序改：

1. 先改 workspace 里的 `PROFILE.md`
2. 再按需要加 `skills/*.md`
3. 只有真的要改“这个 kind 的通用行为”时，才去改 `templates/<kind>/`
4. 根目录 `CLAUDE.md` 尽量保持稳定

简单理解就是：

- 根目录 agent 尽量别乱漂
- 具体 workspace 可以很自由

## 进阶玩法

如果你只是拿它来管几门课，上面的用法已经够了。  
如果你想把它玩得更顺手，下面这些是我自己比较推荐的进阶操作。

### 1. 让每个 workspace agent 长出自己的功能

这个仓库不是要把每个 workspace 都锁死成同一种样子。

你完全可以直接和某个 workspace 里的 agent 对话，让它按照你的需求去定制自己。

例如：

- 改回答口径
- 增加双语解释
- 增加 exam prep 模式
- 增加更偏 proof / coding / application 的讲解方式
- 增加你自己常用的输出格式

我建议优先让它改：

- `PROFILE.md`
- `skills/*.md`

只有真的要改这个 workspace 的底层契约时，再碰 `CLAUDE.md`。

### 2. 不止是课程，你可以自己长出新的 kind

目前默认只有一个 `course` kind。  
但这个仓库不是只给课程用的。

你完全可以直接和根目录教务处对话，让它帮你新增新的 kind。

例如：

- `Health Coach`
- `Interview Coach`
- `Research Assistant`
- `Project Mentor`

用法也很直接：

- 先告诉教务处你想要一个什么样的 workspace
- 让它检查现在有没有合适的 kind
- 如果没有，就让它新建一个
- 然后以后同类 workspace 都沿用这个 kind

这也是这个仓库最有意思的地方之一：  
你不是只在“使用模板”，你其实可以慢慢把模板库本身养出来。

### 3. intake 不一定非要走一种死流程

你可以把文件先丢进 `materials/inbox/`，再让 agent 整理。  
也可以自己先分好，再直接告诉 agent 新文件在哪。

比如：

- “我已经把这周 lecture 放进 `materials/lectures/` 了，你直接看这里”
- “assignment 我已经自己分类好了，你只需要更新 index 和笔记”

这个项目不是流程引擎。  
如果模型够强，很多事没必要机械化。

## 常用脚本

```bash
python3 scripts/scaffold.py list
python3 scripts/scaffold.py list-kinds
python3 scripts/scaffold.py rebuild
python3 scripts/audit.py .
python3 scripts/audit.py "subjects/CSCI/workspaces/RL Reinforcement Learning"
```

如果你要导出 Markdown 笔记：

```bash
uv run python scripts/md_to_pdf.py "subjects/CSCI/workspaces/RL Reinforcement Learning"
```

## 我自己的建议

这个仓库最好用的方式，不是把它当成一个“什么都自动做”的系统。

更好的用法是：

- 让根目录 agent 负责建制
- 让 workspace agent 负责治学
- 让 `notes/chapters/` 成为主知识层
- 让普通问答停留在当前会话里
- 真正需要沉淀时，再更新索引和笔记

这样它会很轻，也比较稳。

还有一个很现实的建议：

这个仓库更适合强模型。  
如果你拿一个理解力和长上下文管理都比较弱的模型来跑，体验很可能会明显下降。

## 更多设计细节

如果你想看：

- 为什么只有两层 agent
- 为什么要有 `kind`
- 为什么我把 `PROFILE.md` 和 `skills/` 拆出来
- 为什么问答默认不落盘

直接去看：

- [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)
- [docs/architecture.md](docs/architecture.md)

## 补充

这个思路我之前也在小红书聊过。  
账号：`7425273470`

帖子：

`效率学习工具｜ Claude Code实现期末开挂 如果早几年...`

链接：

`http://xhslink.com/o/6P5gEKd4bA4`

## 模型说明

这个仓库目前主要只在 `Opus 4.6` 上试用过，体验是很好的。  
我还没有系统验证过它在更低级模型上的表现。

所以这里要提前说清楚：

- 这个仓库可能会依赖高级模型才能运作得比较舒服
- 如果模型本身不够强，可能会更容易读乱、漂移，或者把结构理解错
- 我自己的预期使用场景，本来也是 Claude / ChatGPT / Codex / Opus 这类强模型

如果你用的是较弱模型，建议把它当成实验项目，而不是默认它一定能稳定工作。

## 贡献

如果你想一起改这个模板，先看 [CONTRIBUTING.md](CONTRIBUTING.md)。
