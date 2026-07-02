# Illusion Lab

Illusion Lab 是一个视觉错觉实验集合。每个编号目录都是一个独立的小项目，包含自己的 Vite 入口、源码、测试和可选的生成媒体文件。

## 项目列表

| 编号 | 名称 | 简介 |
| --- | --- | --- |
| `001-aurora-ribbon` | 极光丝带 | 一个发光丝带形态的视觉错觉实验，观看者可能会感知到旋转方向变化。 |
| `002-spin-sphere` | 旋转点阵球 | 一个正交投影的点阵球双向旋转感知错觉，适合录制竖屏短视频。 |
| `003-rotating-crow` | 旋转乌鸦 | 一个旋转舞者式纯黑剪影错觉，观看者可能会感知到顺/逆时针方向反转。 |
| `003-rotating-crow-keyframes` | 旋转乌鸦关键帧版 | 一套重新设计的乌鸦剪影关键帧动画，用翼尖、尾羽和脚爪强化双稳态方向错觉。 |
| `004-wireframe-hourglass-illusion` | 线框双四棱锥 | 一个 Blender 生成的发光线框双四棱锥旋转错觉，顶点先分开再合拢，强调深度暧昧和方向双稳态。 |

## 技术栈说明

本仓库不限定统一技术栈。每个实验可以根据错觉目标和交互需求选择合适的渲染、动画与测试方案。

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

或启动旋转乌鸦项目：

```powershell
npm run dev:003
```

或启动关键帧版旋转乌鸦项目：

```powershell
npm run dev:003-keyframes
```

然后打开终端里显示的本地 Vite 地址，通常是 `http://127.0.0.1:5173/`。

## 常用命令

```powershell
npm run build      # 构建所有项目
npm run build:001  # 只构建 001-aurora-ribbon
npm run build:002  # 只构建 002-spin-sphere
npm run build:003  # 只构建 003-rotating-crow
npm run build:003-keyframes  # 只构建 003-rotating-crow-keyframes
npm run build:004  # 只检查 004-wireframe-hourglass-illusion
npm run test       # 测试所有项目
npm run test:001   # 只测试 001-aurora-ribbon
npm run test:002   # 只测试 002-spin-sphere
npm run test:003   # 只测试 003-rotating-crow
npm run test:003-keyframes   # 只测试 003-rotating-crow-keyframes
npm run test:004   # 只测试 004-wireframe-hourglass-illusion
npm run render:004:preview   # 渲染 004 的低清预览 MP4
npm run render:004:final     # 渲染 004 的竖屏最终 MP4
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
