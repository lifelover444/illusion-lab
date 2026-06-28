# Illusion Lab

Illusion Lab 是一个 Three.js 视觉错觉实验集合。每个编号目录都是一个独立的小项目，包含自己的 Vite 入口、源码、测试和可选的生成媒体文件。

## 项目列表

| 编号 | 名称 | 简介 |
| --- | --- | --- |
| `001-aurora-ribbon` | 极光丝带 | 一个发光丝带形态的视觉错觉实验，观看者可能会感知到旋转方向变化。 |

规划中的目录结构：

```text
illusion-lab/
├─ 001-aurora-ribbon/
├─ 002-rotating-rings/
├─ 003-moire-wave/
└─ 004-depth-grid/
```

目前只有 `001-aurora-ribbon`。

## 快速开始

在仓库根目录安装依赖：

```powershell
npm install
```

启动当前项目：

```powershell
npm run dev
```

也可以明确启动第一个项目：

```powershell
npm run dev:001
```

然后打开终端里显示的本地 Vite 地址，通常是 `http://127.0.0.1:5173/`。

## 常用命令

```powershell
npm run build      # 构建所有项目
npm run build:001  # 只构建 001-aurora-ribbon
npm run test       # 测试所有项目
npm run test:001   # 只测试 001-aurora-ribbon
```

## 新项目约定

新的实验项目使用数字前缀和简短的 kebab-case 英文名：

```text
00N-short-name/
├─ index.html
├─ src/
├─ tests/
├─ package.json
├─ tsconfig.json
└─ vitest.config.ts
```

每个实验尽量保持自包含。只有当多个项目确实需要共享配置或工具时，再把它们放到根目录。
