# Curriculum Victim
LaTeX-based cv typesetting tool

- [适用人群](#适用人群)
- [New in v0.2](#new-in-v02)
- [使用前提和下载方法](#使用前提和下载方法)
- [使用](#使用)
- [源文件格式](#源文件格式)
- [排版设置](#排版设置)
- [ChatGPT](#chatgpt)
- [常见问题](#常见问题)

## 适用人群

- 经常用固定模板制作英文简历、无特殊排版要求、也不享受排版过程的人士
- 赞同“写作者应当专注于内容，排版这种事不如交给程序”这一思想的人士
- 觉得在自己的文档和网页版ChatGPT之间来回复制粘贴很麻烦的人士

## New in v0.2

- 植入ChatGPT, 用法[见下](#chatgpt)
- 实现语法高亮
- 增加关键词`rank`
- 修复一些样式和排版上的bugs

## 使用前提和下载方法

两个前提：

- 不想安装Python的话需要Windows系统；其他操作系统需要安装Python
- 安装[LaTeX](https://www.latex-project.org/), 任何distribution都可以。比如从TexLive[官网](https://www.tug.org/texlive/acquire-netinstall.html)下载[`install-tl-windows.exe`](install-tl-windows.exe), 双击安装（视网络情况，可能需要2-4小时）

以下以没有安装Python的Windows为例：

1. 点击本页上方绿色的Code按钮，然后Download zip
2. 解压下载的文件
3. 在解压得到的文件夹下找到`v0.2`文件夹（以下称为**主目录**），把它拖到一个方便的位置，其他东西（Python源码）可以删了

## 使用

打开主目录，双击`main.exe`, 会看到如下界面：

![1685329910961](https://github.com/gillshen/makelifesuckless/assets/100059605/ad0cf216-b88d-43d7-a87a-1e9af5a28135)

左上是一个纯文本编辑器；左下是console, 用于显示LaTeX编译状况和与ChatGPT交流；右边是排版设置。三个模块的相对大小可以拖动改变。

点击右下角`Run LaTeX`, 编辑器里的内容会被编译成一个**名为`output.pdf`的文件，保存在主目录里**。

我们来演示一下。打开主目录下`samples`文件夹里的简历样本`sample1.txt`（`File` -> `Open`，或者`Ctrl+O`，用别的程序打开后复制粘贴到编辑器里），如下图所示：

![1685330125631](https://github.com/gillshen/makelifesuckless/assets/100059605/0be430aa-ae81-47ff-8798-780525ba8659)

右边的设定可以随便更改，但字体：

- 必须是TrueType或OpenType字体（Windows预装字体多数是TrueType, 没问题，但图中显示的MS Sans Serif不是，会导致编译失败）
- 字体名不能是中文（如选择“宋体”，会导致编译失败）

点击`Run LaTeX`, 如果编译成功，PDF会自动打开，效果大致如下（图中的字体是[EB Garamond](https://fonts.google.com/specimen/EB+Garamond), with old style numbers）：

![1685330334875](https://github.com/gillshen/makelifesuckless/assets/100059605/016d2bc1-4c1f-4879-a100-aaab9be77984)

![1685330391113](https://github.com/gillshen/makelifesuckless/assets/100059605/fd55b47f-2fe3-4e67-a287-e313e6fc116b)

每一次编译都会覆盖主目录下的`output.pdf`（如果已存在）。如果想保留它，请及时另存。

## 源文件格式

这里说的源文件是指编辑器里的内容。编辑器里的内容能直接编译，不需要保存为文件。

我设计的初衷是，用户照着`sample1.txt`依样画葫芦，或者`File` -> `New`新建一个模板就能用，不需要特别学习什么格式。

But just in case:

源文件的**每一行**必须：
- 以**关键词**加**冒号**开头，关键词不区分大小写，冒号不区分全角半角；或者
- 以列表符号`-`或`•`开头（用于详细描述活动/经历）；或者
- 以`#`开头（用于活动分类）；或者
- 是空白行。

这里说的行，确切地说是**两个相邻换行符之间**或者**文本开头到第一个换行符之间**或者**最后一个换行符到文本末尾之间**的字符串。比如本段文字，在你的屏幕上可能显示为两三行，但因为中间没有换行符（没有回车），在我们说的意义上仍是一行。

### 关键词

| 模块 | 关键词 | 说明 |
| ---- | ------ | ---- |
| 个人信息 | `name` `email` `phone` `address` `website` | 这个模块只能出现一次，模块内部关键词顺序任意 |
| 教育背景 | `school` `loc` `start date` `end date` `degree` `major` `minor` `gpa` `rank` `courses` | 可多次出现，`school`必须先于其他关键词，其他顺序任意 |
| 活动/经历 | `role` `org` `loc` `start date` `end date` `hours per week` `weeks per year`| 可多次出现，`role`必须先于其他关键词，其他顺序任意 |
| 考试 | `test` `score` `test date` | 可多次出现，`test`必须先于`test date` |
| 奖项 | `award`  `award date` | 可多次出现，`award`必须先于`award date` |
| 技能 | `skillset name` `skills` | 可多次出现，`skillset name`必须先于`skills` |

关键词后的内容可以为空，无内容的关键词编译时会自动忽略。

### 活动分类

所有活动默认归成一类，默认分类名"Activities". 自定义分类请用`#`符号。比如：

```
# Work Experience

role: xxx
...

role: yyy
...

# Community Service

role: zzz
...
```

### 日期格式

推荐使用`yyyy-mm-dd`或`yyyy-mm`. 这样的好处是
- 程序可以帮你编译成其他格式，比如`2022-11-01`可以编译成"Nov 1, 2022", "November 1, 2022", "2022/11/01"等等
- 程序可以自动减少年份的重复，如起止时间是`2022-11`和`2022-12`，则编译结果将是"Nov – Dec 2022"（该福利仅在输出单词拼写的月份时有效）
- 如果输入的日期不存在，比如`2022-13`，编译时会报错

不符合`yyyy-mm-dd`或`yyyy-mm`格式的日期在编译时会原样保留。

以上福利只适用于关键词`xxx date`的内容，不适用于文本中其他地方出现的日期。

### 斜体，粗体，链接，特殊字符

源文件是纯文本，要实现斜体等格式，需要一些额外动作（模仿Markdown语法，也支持多数LaTeX语法，不详细介绍）。常用的罗列如下：

|| 源文件 | 编译结果 |
| - | ------ | -------- |
| 斜体 | `*italic*` | *italic* |
| 粗体 | `**bold**` | **bold** |
| 粗斜体 | `***bold italic***` | ***bold italic*** |
| Small Caps | `\textsc{small caps}` | [see here](https://en.wikipedia.org/wiki/Small_caps) |
| 星号 | `\*` | * |
| 链接 | `[GitHub](https://github.com/)` | [GitHub](https://github.com) |
| [Em dash](https://www.merriam-webster.com/words-at-play/em-dash-en-dash-how-to-use) | `---`或字符本身 | — |
| [En dash](https://www.merriam-webster.com/words-at-play/em-dash-en-dash-how-to-use) | `--`或字符本身 | – |
| 左花括号 | `\{` | { |
| 右花括号 | `\}` | } |
| 右斜杠 | `\textbackslash{}` | \ |

**`\`, `{`和`}`在LaTeX中是特殊字符，不按以上方式输入可能会导致编译失败。**

此外，直引号会自动转换为[适当的弯引号](https://typographyforlawyers.com/straight-and-curly-quotes.html)。

### 其他注意事项

- 目前不支持中文字符（关键词后的全角冒号除外）
- 每个活动需要至少一条描述（以列表符号`-`或`•`开头），否则编译会报错

## 排版设置

- **Show Activity Locations** - 顾名思义
- **Show Time Commitments** - 决定是否显示活动的hours per week和weeks per year
- **Text Font** - 决定主文本的字体
- **Heading Font** - 决定小标题（如"Education", "Awards"之类）的字体，字体大小是相对于主文本字体而言的，Size 1和主文本字体一样大
- **Title Font** - 用于简历主人的名字
- **Number Style** - [详细说明](https://www.monotype.com/resources/expertise/how-use-figure-styles-illustrator)（某些字体不支持，但不会导致编译失败）
- **Paper Size** - 有A4和Letter两种
- **Margins** - 页边距
- **Line Height** - 行距，1.0=单倍，2.0=双倍，etc.
- **Space Between Paragraphs** - 段落间距（如考试/奖项/技能集之间的间距）
- **Space Between Entries** - 活动之间/教育经历之间的间距
- **Space Before Section Titles**, **Space After Section Titles** - 顾名思义，小标题和前后文字的间距
- **Section Title Style** - 决定小标题是否加粗，是否全大写
- **Default Activities Section Title** - 活动的默认分类名（如已自定义分类，此设定无效）
- **Awards Section Title**, **Skills Section Title** - 奖项和技能模块的小标题
- **Bold Award Names**, **Bold Skillset Names** - 奖项和技能类别是否加粗
- **Contact Divider** - 个人信息模块的分割符，默认"|"，可以改成任意字符组合（某些LaTeX特殊字符除外）也可以留空
- **Bullet Text** - 活动描述的列表符号，默认"•" (U+2022)，可以改成任意字符组合（某些LaTeX特殊字符除外）也可以留空
- **Bullet Indent** - 列表符号相对于最文本左侧边缘的缩进，单位是[em](https://en.wikipedia.org/wiki/Em_(typography))
- **Bullet-Item Separation** - 列表符号和列表内容之间的距离，单位也是em
- **Handle Ending Periods** - 决定是否自动补齐/删除活动描述句末的句号
- **Date Format** - 顾名思义（只适用于源文件中符合`yyyy-mm-dd`或`yyyy-mm`格式的日期）
- **Use Text Font for URLs** - 决定链接字体：如果打勾，使用主文本字体；如不打勾，使用LaTeX自带的等宽字体
- **Enable URL Color**, **URL Color** - 前者决定链接样式：不打勾，链接呈黑色，带边框；打勾，链接无边框，可以通过后者设定链接颜色
- **Show Page Numbers** - 决定是否显示页码

## ChatGPT

要使用这个功能，你需要一个OpenAI的API key. 两个获取途径：

- 注册OpenAI账号，然后[在用户设置中获取](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key)；需要付费，虽然不贵（gpt-3.5-turbo的价钱是$0.002 per 1000 tokens）但在中国境内支付会比较麻烦
- 使用GitHub网友Pawan Osman搭建的反向代理服务器，加入TA的Discord即可获得API Key, 免费；具体操作见[该项目页面](https://github.com/PawanOsman/ChatGPT)（我不能保证TA不会监视你和OpenAI之间的通讯，介意的话不要使用）

不管选哪个，你需要在**主目录**下创建一个名为`keys.json`的文件，把你的API key粘贴进去。格式如下：

如果是官方API key（"sk-"开头的一长串字符）：

```
{
    "key": "粘贴API key到双引号里"
}
```

如果是Pawan的代理API key（"pk-"开头的一长串字符）：

```
{
    "key": "粘贴API key到双引号里",
    "base": "https://api.pawan.krd/v1"
}
```

快捷键`Ctrl+E`（或工具栏`ChatGPT` -> `Enter Prompt...`）可以打开prompt输入窗。输入prompt后发送，正常的话几秒内console会显示ChatGPT的回复。

![1685333679167](https://github.com/gillshen/makelifesuckless/assets/100059605/53107b3d-cabf-4c6b-90b6-aa5a626a7f62)

如果编辑器里有文字被选中，选中的文字自动附在用户输入的prompt后面发给ChatGPT, 如图（输入窗中是用户输入的prompt, console显示的是实际发给ChatGPT的prompt）：

![1685331544969](https://github.com/gillshen/makelifesuckless/assets/100059605/6aeab41e-0c6a-4d79-ab59-8714a2233207)

如果经常输入同一prompt，建议把这个prompt写成一个txt文件，取一个合适的文件名，比如`Proofread.txt`, 放到主目录下的`prompts`文件夹里。重启程序后工具栏和右键快捷菜单里就会出现`Proofread`命令，点击即可实现prompt输入发送。

`prompts`文件夹里预置了三个prompt文件：`Polish.txt`, `Translate.txt`, `Name the Role.txt`，可以按需修改或删除。

## 常见问题

### "Sorry, something went wrong", console显示"invalid font identifier"

<img src="https://github.com/gillshen/makelifesuckless/assets/100059605/cc2023b5-cfa5-41ba-949d-7f2faeb9c2fe" width=804>

大概是因为选了一个非TrueType字体。首次使用时Windows默认的字体MS Sans Serif就会导致这个错误。解决方法：检查三个字体选择，确保每个都是TrueType.

### "Sorry, something went wrong", console显示"no output PDF file produced"

<img src="https://github.com/gillshen/makelifesuckless/assets/100059605/a44f9f38-8149-4cec-b3c2-d2334add14d0" width=804>

大概是因为之前编译成功并打开了`output.pdf`, 某些PDF浏览器（比如Adobe Reader）会锁住打开的文件，导致覆盖失败。解决方法：把PDF关了再编译。

### SSL错误导致API请求无法送达

<img src="https://github.com/gillshen/makelifesuckless/assets/100059605/d3b7d635-9253-4a47-b5ab-5279563d99b0" width=631>

大概是vpn问题。解决方法：把vpn关了。

### 密钥与IP地址不匹配（使用Pawan代理ChatGPT时会出现的错误）

<img src="https://github.com/gillshen/makelifesuckless/assets/100059605/bc3f59b0-986b-4386-bfa9-9bec07ae9609" width=631>

解决方法：按报错里的指示，去Discord重置IP授权。
