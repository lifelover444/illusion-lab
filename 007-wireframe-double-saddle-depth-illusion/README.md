# Wireframe Double Saddle Depth Illusion

一个用 Blender 生成的双鞍形粒子表面旋转错觉实验。画面下方保留 006 的当前鞍面模型，画面上方放置同款模型并切到可见倒扣相位；两个模型挂在同一个旋转 rig 上，以完全同步的节奏旋转。

## 文件结构

```text
007-wireframe-double-saddle-depth-illusion/
├─ scripts/
│  ├─ create_scene.py       # Blender 场景生成与渲染脚本
│  ├─ saddle-config.json    # 几何、相机、双模型实例、运动、输出规格
│  └─ run-blender.mjs       # Node 包装脚本
├─ src/
│  └─ saddleGeometry.ts     # 几何约束的可测试版本
├─ tests/
│  └─ saddleGeometry.test.ts
├─ scene/                   # 生成的 .blend 文件
└─ output/                  # 生成的 MP4 文件
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
npm run scene:007
```

渲染低清预览：

```powershell
npm run render:007:preview
```

渲染竖屏最终版：

```powershell
npm run render:007:final
```

## 错觉设计

- 复用 006 的双曲抛物面粒子云、圆角外轮廓和中性随机粒子色。
- 下模型保持当前姿态，上模型使用 90 度可见倒扣相位并上移，形成上下不同的对称双模型结构。
- 两个模型共用同一个旋转 rig，24 秒匀速旋转两圈，首尾姿态闭合。
- 每个模型使用独立随机种子采样粒子，避免上下两层出现完全相同的可追踪噪声纹理。
- 正交相机继续轻微仰视，画幅缩放扩大以完整容纳上下双模型。
