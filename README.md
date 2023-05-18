# Curriculum Victim
LaTeX-based cv typesetting tool

## 适用人群

- 经常用固定模板制作英文简历、无特殊排版要求、也不享受排版过程的人士
- 赞同“写作者应当专注于内容，排版这种事不如交给程序”这一思想的人士

## 使用前提

- Windows系统（不需要Python）或安装了Python的任何操作系统
- 安装[LaTeX](https://www.latex-project.org/), 任何distribution都可以。比如从TexLive[官网](https://www.tug.org/texlive/acquire-netinstall.html)下载[`install-tl-windows.exe`](install-tl-windows.exe), 双击安装（可能需要1-2小时）

以下以**没有**安装Python的Windows为例。

## 下载

1. 点击本页上方绿色的Code按钮，然后Download zip
2. 解压下载的文件
3. 在解压得到的文件夹下找到`v0.1`文件夹（以下称为**主目录**），把它拖到一个方便的位置，其他东西（Python源代码）可以删了

## 使用

打开主目录，双击`main.exe`, 会看到如下界面：

![1684372675258](https://github.com/gillshen/makelifesuckless/assets/100059605/e3c56b69-4d3f-4e70-9e03-cdcccde4161a)

左上是一个纯文本编辑器；左下log区域（一般不用理会）；右边是排版设定。三个模块的相对大小可以拖动改变。

点击右下角`Run LaTeX`, 编辑器里的内容就会被编译成**一个名为`output.pdf`的文件，保存在主目录里**。

我们来演示一下。打开主目录下`samples`文件夹里的简历样本`sample1.txt`（`File` -> `Open`，或者用别的程序打开后复制粘贴到编辑器里），如下图所示：

![1684372787848](https://github.com/gillshen/makelifesuckless/assets/100059605/e81d5b0e-85fa-4d91-bc8f-b80e9bb0da97)

右边的设定可以随便更改，但字体：
- 必须是TrueType或OpenType字体（Windows预装字体多数是TrueType, 没问题）
- 字体名不能是中文（如图中是“宋体”，会导致编译失败）

点击`Run LaTeX`, 如果编译成功，PDF会自动打开，效果大致如下（图中的字体是[EB Garamond](https://fonts.google.com/specimen/EB+Garamond)）：

![1684339663004](https://github.com/gillshen/makelifesuckless/assets/100059605/46c31411-89e1-48a2-91d2-8fbca5a2fcb5)

每一次编译都会覆盖主目录下的`output.pdf`（如果已存在）。如果想保留它，请及时另存。

如果编译失败：

- 如果log里的报错信息说font如何如何，换别的字体试试。
- 如果之前编译成功并打开了`output.pdf`, 把它关上再编译。某些PDF浏览器（比如Adobe Reader）会锁住打开的文件，导致覆盖失败。

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

#### 关键词

| 模块 | 关键词 | 说明 |
| ---- | ------ | ---- |
| 个人信息 | `name` `email` `phone` `address` `website` | 这个模块只能出现一次，模块内部关键词顺序任意 |
| 教育背景 | `school` `loc` `start date` `end date` `degree` `major` `minor` `gpa` `courses` | 可多次出现，`school`必须先于其他关键词，其他顺序任意 |
| 活动/经历 | `role` `org` `loc` `start date` `end date` `hours per week` `weeks per year`| 可多次出现，`role`必须先于其他关键词，其他顺序任意 |
| 考试 | `test` `score` `test date` | 可多次出现，`test`必须先于`test date` |
| 奖项 | `award`  `award date` | 可多次出现，`award`必须先于`award date` |
| 技能 | `skillset name` `skills` | 可多次出现，`skillset name`必须先于`skills` |

关键词后的内容可以为空，无内容的关键词编译时会自动忽略。

#### 活动分类

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

#### 日期格式

推荐使用`yyyy-mm-dd`或`yyyy-mm`. 这样的好处是
- 程序可以帮你编译成其他格式，比如`2022-11-01`可以编译成"Nov 1, 2022", "November 1, 2022", "2022/11/01"等等
- 程序可以自动减少年份的重复，如起止时间是`2022-11`和`2022-12`，则编译结果将是"Nov – Dec 2022"（该福利仅在输出单词拼写的月份时有效）
- 如果输入的日期不存在，比如`2022-13`，编译时会报错

不符合`yyyy-mm-dd`或`yyyy-mm`格式的日期在编译时会原样保留。

以上福利只适用于关键词`xxx date`的内容，不适用于文本中其他地方出现的日期。

#### 斜体，粗体，链接，特殊字符

源文件是纯文本，要实现斜体等格式，需要使用一点特殊的语法（模仿Markdown，也支持多数LaTeX语法，不详细介绍）。常用的罗列如下：

|| 源文件 | 编译结果 |
| - | ------ | -------- |
| 斜体 | `*italic*` | *italic* |
| 粗体 | `**bold**` | **bold** |
| 粗斜体 | `***bold italic***` | ***bold italic*** |
| 星号 | `\*` | * |
| 链接 | `[GitHub](https://github.com/)` | [GitHub](https://github.com) |
| [Em dash](https://www.merriam-webster.com/words-at-play/em-dash-en-dash-how-to-use) | `---`或字符本身 | — |
| [En dash](https://www.merriam-webster.com/words-at-play/em-dash-en-dash-how-to-use) | `--`或字符本身 | – |
| 左花括号 | `\{` | { |
| 右花括号 | `\}` | } |

**左右花括号在LaTeX中是特殊字符，不加`\`直接输入可能会导致编译失败。**

此外，直引号会自动转换为[适当的弯引号](https://typographyforlawyers.com/straight-and-curly-quotes.html)。

#### 其他注意事项

- 目前不支持中文字符（关键词后的全角冒号除外）
- 每个活动需要至少一条描述（以列表符号`-`或`•`开头），否则编译会报错

## 排版设定

- **Show Activity Locations** - 顾名思义
- **Show Time Commitments** - 决定是否显示活动的hours per week和weeks per year
- **Text Font** - 决定主文本的字体
- **Heading Font** - 决定小标题（如"Education", "Awards"之类）的字体，字体大小是相对于主文本字体而言的，Size 1和主文本字体一样大
- **Title Font** - 用于简历主人的名字
- **Number Style** - [详细](https://www.monotype.com/resources/expertise/how-use-figure-styles-illustrator)（某些字体不支持，但不会导致编译失败）
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
- **Date Format** - 顾名思义（只适用于源文件中符合`yyyy-mm-dd`或`yyyy-mm`格式的日期）
- **Use Text Font for URLs** - 决定链接字体：如果打勾，使用主文本字体；如不打勾，使用LaTeX自带的等宽字体
- **Enable URL Color**, **URL Color** - 前者决定链接样式：不打勾，链接呈黑色，带边框；打勾，链接无边框，可以通过后者设定链接颜色
