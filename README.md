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
| `004-wireframe-hourglass-depth-comparison` | 线框双四棱锥对照版 | 中间保留无纵深线框错觉，左右用同一投影动画但相反前后关系的实体色彩对照组引导顺/逆时针感知。 |
| `005-heart-blender-illusion` | 莫比乌斯心形环 | 一个 Blender 生成的粉色发光莫比乌斯心形环，使用半透明连续丝带、正交相机和弱深度线索保持顺/逆时针双稳态感知。 |
| `006-wireframe-saddle-depth-illusion` | 线框鞍形粒子面 | 一个 Blender 生成的发光鞍形粒子表面旋转错觉，用双曲抛物面、圆角外轮廓和中性粒子噪声制造中心凸出/凹入的深度翻转。 |
| `007-wireframe-double-saddle-depth-illusion` | 双鞍形粒子面 | 一个上下双模型版鞍形粒子表面错觉，下方保持 006 当前模型，上方切到可见倒扣相位，并用同一旋转 rig 同步旋转。 |
| `008-wireframe-hyperboloid-depth-rotation-illusion` | 单叶双曲面线框笼 | 一个 Blender 生成的单叶双曲面粒子线框笼旋转错觉，用等半径粉白粒子虚环、双向断续粒子肋和中性表面粒子削弱前后线索，制造顺/逆时针双稳态感知。 |

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
npm run build:004-comparison  # 只检查 004-wireframe-hourglass-depth-comparison
npm run build:005  # 只检查 005-heart-blender-illusion
npm run build:006  # 只检查 006-wireframe-saddle-depth-illusion
npm run build:007  # 只检查 007-wireframe-double-saddle-depth-illusion
npm run build:008  # 只检查 008-wireframe-hyperboloid-depth-rotation-illusion
npm run test       # 测试所有项目
npm run test:001   # 只测试 001-aurora-ribbon
npm run test:002   # 只测试 002-spin-sphere
npm run test:003   # 只测试 003-rotating-crow
npm run test:003-keyframes   # 只测试 003-rotating-crow-keyframes
npm run test:004   # 只测试 004-wireframe-hourglass-illusion
npm run test:004-comparison   # 只测试 004-wireframe-hourglass-depth-comparison
npm run test:005   # 只测试 005-heart-blender-illusion
npm run test:006   # 只测试 006-wireframe-saddle-depth-illusion
npm run test:007   # 只测试 007-wireframe-double-saddle-depth-illusion
npm run test:008   # 只测试 008-wireframe-hyperboloid-depth-rotation-illusion
npm run render:004:preview   # 渲染 004 的低清预览 MP4
npm run render:004:final     # 渲染 004 的竖屏最终 MP4
npm run render:004-comparison:preview   # 渲染 004 对照版低清预览 MP4
npm run render:004-comparison:final     # 渲染 004 对照版竖屏最终 MP4
npm run scene:005             # 生成 005 的 Blender 场景
npm run render:005:preview    # 渲染 005 的低清预览 MP4
npm run render:005:final      # 渲染 005 的竖屏最终 MP4
npm run scene:006             # 生成 006 的 Blender 场景
npm run render:006:preview    # 渲染 006 的低清预览 MP4
npm run render:006:final      # 渲染 006 的竖屏最终 MP4
npm run scene:007             # 生成 007 的 Blender 场景
npm run render:007:preview    # 渲染 007 的低清预览 MP4
npm run render:007:final      # 渲染 007 的竖屏最终 MP4
npm run scene:008             # 生成 008 的 Blender 场景
npm run render:008:preview    # 渲染 008 的低清预览 MP4
npm run render:008:final      # 渲染 008 的竖屏最终 MP4
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
