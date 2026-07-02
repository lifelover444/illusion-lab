# Wireframe Square Pyramid Illusion

一个用 Blender 生成的发光线框双四棱锥旋转错觉实验。上方是倒置四棱锥，下方是正立四棱锥；两个顶点从相接开始，在第一圈 11 秒内缓慢分开，再在第二圈 11 秒内合拢回初始状态。

## 文件结构

```text
004-wireframe-hourglass-illusion/
├─ scripts/
│  ├─ create_scene.py          # Blender 场景生成与渲染脚本
│  ├─ hourglass-config.json    # 几何、运动、相机、输出规格
│  └─ run-blender.mjs          # Node 包装脚本
├─ src/
│  └─ hourglassGeometry.ts     # 几何约束的可测试版本
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
npm run scene --workspace @illusion-lab/wireframe-hourglass-illusion
```

渲染低清预览：

```powershell
npm run render:preview --workspace @illusion-lab/wireframe-hourglass-illusion
```

渲染竖屏最终版：

```powershell
npm run render:final --workspace @illusion-lab/wireframe-hourglass-illusion
```

根目录快捷命令：

```powershell
npm run scene:004
npm run render:004:preview
npm run render:004:final
```

## 错觉设计

- 使用两个共享中心轴的四棱锥线框，而不是实体面。
- 总时长 22 秒，旋转两圈，每圈约 11 秒。
- 第一圈两个顶点缓慢分开，第二圈两个顶点缓慢合上。
- 使用轻微俯视的正交相机，让方形底边可见，同时减少强透视深度线索。
- 所有边线都显示，不隐藏背面线。
- 白色主线叠加彩色发光边缘。
- 内部粒子使用四臂螺旋星尘、断续顶点粒子桥和接触脉冲，让开合动作更明显，但不模拟真实重力。
- 匀速旋转，避免加减速破坏双稳态感知。
