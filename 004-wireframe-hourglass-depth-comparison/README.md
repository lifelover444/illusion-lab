# Wireframe Hourglass Depth Comparison

一个用 Blender 生成的双四棱锥旋转对照实验。画面中间保留原版无实体面的发光线框错觉，左侧加入有实体色彩和遮挡关系的顺时针对照组，右侧加入同样有纵深线索的逆时针对照组。三组都使用正交相机，不依赖透视缩放。

## 文件结构

```text
004-wireframe-hourglass-depth-comparison/
├─ scripts/
│  ├─ create_scene.py          # Blender 场景生成与渲染脚本
│  ├─ hourglass-config.json    # 三组布局、几何、运动、相机、输出规格
│  └─ run-blender.mjs          # Node 包装脚本
├─ src/
│  └─ hourglassGeometry.ts     # 线框和实体对照几何约束的可测试版本
├─ tests/
│  └─ hourglassGeometry.test.ts
├─ scene/                      # 生成的 .blend 文件
└─ output/                     # 生成的 MP4 文件
```

## 命令

默认使用：

```powershell
D:\software\Blender 4.5 LTS\blender.exe
```

如果 Blender 在别的位置，先设置：

```powershell
$env:BLENDER_EXE = "D:\path\to\blender.exe"
```

生成 `.blend` 场景文件：

```powershell
npm run scene --workspace @illusion-lab/wireframe-hourglass-depth-comparison
```

渲染低清预览：

```powershell
npm run render:preview --workspace @illusion-lab/wireframe-hourglass-depth-comparison
```

渲染竖屏最终版：

```powershell
npm run render:final --workspace @illusion-lab/wireframe-hourglass-depth-comparison
```

根目录快捷命令：

```powershell
npm run scene:004-comparison
npm run render:004-comparison:preview
npm run render:004-comparison:final
```

## 错觉设计

- 中间组使用两个共享中心轴的四棱锥线框，而不是实体面。
- 左侧对照组使用闭合实体面、暖色哑光受光分面、弱化远边和顶点体积提示，用一套前后遮挡关系引导观众把同一投影理解成顺时针。
- 右侧对照组使用闭合实体面、冷色哑光受光分面、弱化远边和顶点体积提示，用沿相机视线反转后的前后遮挡关系引导观众把同一投影理解成逆时针。
- 三组共用同一条时间轴：总时长 22 秒，旋转两圈，每圈约 11 秒，开合关键帧和旋转速度完全同步。
- 三组都在第一圈让两个顶点缓慢分开，第二圈让两个顶点缓慢合上；左右不改变二维运动，只改变深度解释，方便观众用左侧把中间看成顺时针、用右侧把中间看成逆时针。
- 使用轻微俯视的正交相机，让方形底边可见，同时避免透视缩放。
- 中间组所有边线都显示，不隐藏背面线，保留方向双稳态。
- 中间组白色主线叠加彩色发光边缘和粒子桥；左右组用实体面遮挡和颜色深浅提供明确纵深。
- 匀速旋转，避免加减速破坏双稳态感知。
