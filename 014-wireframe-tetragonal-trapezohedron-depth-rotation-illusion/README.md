# 014 四方偏方面体纵深歧义旋转错觉

一个自包含的 Blender/TypeScript 实验：用正交投影显示正四方偏方面体的全部 16 条棱，让中央交替之字带在匀速刚体旋转中产生多种合理的前后解释。8 个风筝面覆盖统一的 76% 高透明暗冰蓝面板；约 7,600 个冷白表面星点按与 011 相近的面积密度、尺寸和亮度铺满各面。断续棱点、顶点晶体和连续轮廓被拆到不受面板遮挡的独立视图层，避免后侧轮廓因穿过多层透明面而变暗并泄露唯一深度方向。连续结构线以固定 10% 可见度合成，投影外轮廓提高到 20%，交叉处采用单一蒙版而不累加亮度。整体因此读成一个连贯旋转的星尘晶体，同时保留顺、逆时针两种解释。画面还包含静止于刚体坐标系的断续轴向星线和中央稀疏星云；没有灯光、阴影、折射、菲涅耳、透视缩放或深度颜色梯度。只有中央星云尘粒沿 Z 轴做极弱漂浮，禁止绕轴运动，并以 12 秒周期精确闭环。

## 几何

- 10 个顶点、16 条唯一棱、8 个共面风筝面，Euler 特征为 2。
- `beltHalfHeight` 始终由 `H * (3 - 2 * sqrt(2))` 推导。
- 上下四点环半径相同，下环固定错开 45°；不绘制任何水平腰环棱。
- 所有风筝面既用于按面积采样稀疏尘粒，也组成一个双面透明壳；面板不使用定向光照、阴影、高光或折射，因此只提供弱遮挡连续性，不绑定唯一旋向。
- 表面星点密度约为每单位面积 414 个，点径为 `0.0022-0.0045`，统一使用强度 `1.0` 的冷白光；每条面边界内侧保留 `0.035` 宽、降低约 22% 密度的窄槽，使高密度点面仍能衬托轮廓。
- 全部 16 条棱均由随机断续的冷蓝紫核心点构成，并每隔 5 个核心点叠加一个低透明柔光点；点状轮廓整体以 6 秒周期做约 ±6% 的同步呼吸，没有沿棱流动的高光。
- 每条棱下方另有一根半径 `0.002` 的不透明白色蒙版导线。它不直接进入主体渲染，而是在合成器中统一着色为冷蓝灰：全部结构线固定为 10% 可见度，闭合壳体的投影外轮廓固定为 20%。面板不会压暗远侧线，交叉位置也不会因相加而变亮；导线不呼吸、不发辉光、没有方向权重。
- 主体、断续棱点、连续导线和闭合壳体蒙版分别使用 `Surface`、`EdgeDetail`、`GuideMask`、`SilhouetteMask` 四个视图层。后两层只输出蒙版，由合成器执行深度无关的固定透明度叠加。

指定的 45° 环错位具有 D4d/S8 旋转反射对称，而不是逐点的中心反演：绕 Z 轴旋转 45°并反射 `z` 会把整个顶点集映回自身。四点下环若同时要求每个 `v` 都存在 `-v`，其方位必须与上环相差 0°（模 90°），这与正四方偏方面体所需的 45°错位矛盾。测试明确验证真实的 S8 对称、原点质心和全部准确拓扑条件。

## 命令

从仓库根目录运行：

```text
npm run test:014
npm run build:014
npm run scene:014
npm run render:014:stills
npm run render:014:preview
npm run render:014:final
```

默认 Blender 路径为 `D:\software\Blender 4.5 LTS\blender.exe`。其他安装位置可设置 `BLENDER_EXE`。

## 生成文件

- `scene/wireframe-tetragonal-trapezohedron-depth-rotation-illusion.blend`
- `output/stills/tetragonal-trapezohedron-contact-sheet.png`
- `output/stills/tetragonal-trapezohedron-motion-contact-sheet.png`
- `output/wireframe-tetragonal-trapezohedron-preview.mp4`
- `output/wireframe-tetragonal-trapezohedron-depth-rotation-illusion.mp4`
- `output/preview-motion-contact-sheet.png` 与 `output/final-motion-contact-sheet.png`
- `output/inspection.json` 与逐档 `video-inspection-*.json`

视频使用线性世界 Z 轴旋转。帧序列不包含重复的 360°尾帧；概念上的下一帧与首帧像素级一致，从而无缝循环且不会在接缝处停顿。

## 本地结构

```text
src/tetragonalTrapezohedronGeometry.ts
tests/tetragonalTrapezohedronGeometry.test.ts
scripts/create_scene.py
scripts/tetragonal-trapezohedron-config.json
scripts/run-blender.mjs
scene/   # 生成
output/  # 生成
```
