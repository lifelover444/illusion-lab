# Wireframe Hyperboloid Depth Rotation Illusion

一个用 Blender 生成的单叶双曲面线框笼旋转错觉实验。模型由上下等半径粉白粒子虚环、双向断续粒子肋和中性粒子噪声构成，默认不显示中间腰环。视觉质感参考 006 的黑底、细亮轮廓和细碎彩色粒子，但几何形体是独立的单叶双曲面笼。

当前定版重点是降低上下圆口的抢眼程度：圆口不再使用高亮白色硬边，而是使用很细的低饱和粉白线芯，加一圈松散粒子虚边来提示开口结构。侧边连续线条默认关闭，只保留两组强度接近的断续粒子肋，避免单一方向的追踪锚点压过双稳态错觉。

## 文件结构

```text
008-wireframe-hyperboloid-depth-rotation-illusion/
├─ scripts/
│  ├─ create_scene.py          # Blender 场景生成与渲染脚本
│  ├─ hyperboloid-config.json  # 几何、相机、粒子、运动、输出规格
│  └─ run-blender.mjs          # Node 包装脚本
├─ src/
│  └─ hyperboloidGeometry.ts   # 双曲面笼几何约束的可测试版本
├─ tests/
│  └─ hyperboloidGeometry.test.ts
├─ scene/                      # 生成的 .blend 文件
└─ output/                     # 生成的 MP4/PNG 文件
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
npm run scene:008
```

渲染低清预览：

```powershell
npm run render:008:preview
```

输出：

```text
output/wireframe-hyperboloid-preview.mp4
360x640, 15fps, 24s, 360 frames
```

渲染竖屏最终版：

```powershell
npm run render:008:final
```

输出：

```text
output/wireframe-hyperboloid-depth-rotation-illusion.mp4
720x1280, 30fps, 24s, 720 frames
```

## 错觉设计

- 上下圆环半径相同，顶环相对底环旋转 84 度，数学骨架仍是直线生成的单叶双曲面。
- 上下圆环使用低饱和粉白细线加粒子虚边，线芯很细、glow 很弱，降低纯白实线的抢眼程度。
- 中间腰环默认不绘制，只保留粒子密度和轮廓收缩来表达单叶双曲面的收腰。
- 可见侧边不绘制连续斜线，只保留两组强度相等的双向断续粒子肋，让顺/逆时针两种深度解释都成立。
- 语义爱心纹样默认关闭，避免成为可追踪方向锚点。
- 不使用实体面、遮挡排序、阴影或前后色差，保留顺/逆时针双稳态所需的深度歧义。
- 参考 006 的质感：黑底、细亮轮廓、弱 glow、细碎中性彩色粒子。
- 粒子采样贴在双曲面上，粒子密度承担主要外壳读形，不使用实体面或前后遮挡排序。
- 24 秒竖屏循环，12 秒一圈，首尾姿态闭合。

## 当前关键参数

```text
ribCount: 12
twistDegrees: 84
particleCount: 9200
ringStyle: soft-pink-particle-rim
ringParticleCount: 340
waistRingVisible: false
continuousSideRibs: false
guideRibFamilies: positive + negative
heartPattern: false
rotationCycleSeconds: 12
```
