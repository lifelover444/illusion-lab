# 菱形十二面体纵深歧义旋转错觉

这是 Illusion Lab 的独立实验 015：一个采用标准菱形十二面体拓扑、在 XY 径向轻度压缩至 92% 的凸菱形晶体，在纯黑背景中绕世界 Z 轴匀速旋转。六个四价轴向顶点、八个三价角点和 24 条真实棱共同形成会重新解释前后关系的中央菱形/立方骨架；稳定的 Z± 尖点和略收窄的腰部帮助它持续读成一枚完整、修长的冰晶。

视觉处理与实验 014 对齐，但不复制其几何或内部星云：约 9300 个统一冷白星点按变形后总面积折算到与 014 接近的面密度，点径、亮度、边缘窄槽和暗冰蓝面板沿用 014 参数。面板约 76% 透明，使用双面抖动透明与重叠衰减，使整体先读成密实的星尘晶体而不是明亮线框或空壳。

24 条真实棱各自使用断续冷蓝紫微粒和稀疏柔光点；连续结构线被拆到独立蒙版视图层，内部固定 10% 可见度，投影外轮廓固定 20%，交叉处不累积亮度，也不受多层面板压暗。棱点只做 6 秒周期、约 ±6% 的整体同步呼吸，没有沿棱流动。透明面板没有灯光、阴影、反射、折射、Fresnel、环境遮蔽、景深或方向配色；项目仍没有内部尘粒、轴向星线、顶点强调、深度颜色梯度或独立粒子运动。

XY 径向压缩保持 V=14、E=24、F=12、中心反演、等长棱、闭合流形以及每个面的平面菱形性质；四个 XY 面与八个斜面形成两种面积，因此它是标准实体的 D4h 对称视觉变体，而不是 12 面全等的标准度量模型。

## 结构

```text
src/rhombicDodecahedronGeometry.ts          # 径向变体几何、内部判定、正交投影和循环数学
tests/rhombicDodecahedronGeometry.test.ts   # 拓扑、度数、面、对称、投影与循环测试
scripts/create_scene.py                     # 独立 Blender 场景、静帧、接触表与循环检查
scripts/rhombic-dodecahedron-config.json    # 014 对齐画面与多档动画参数
scripts/run-blender.mjs                     # Blender 命令入口和视频规格验证
scene/                                      # 生成的 .blend
output/                                     # 低清静帧、检查数据、接触表和 MP4
```

## 命令

在仓库根目录运行：

```powershell
npm run test:015
npm run build:015
npm run scene:015
npm run render:015:stills
npm run render:015:preview
npm run render:015:hd
npm run render:015:hd60
```

默认 Blender 路径为 `D:\software\Blender 4.5 LTS\blender.exe`，也可设置 `BLENDER_EXE`。预览为 360×640、15 fps、12 samples；高清 profile 提供 720×1280、30 fps 与 60 fps 两档，均为 24 秒、24 samples。所有档位保持相同几何、材质、粒子、面板和转速，各编码两整圈，并省略与首帧重复的循环尾帧。仍不提供 `final` 命令。

## 低清输出

- `output/stills/rhombic-dodecahedron-contact-sheet.png`
- `output/rhombic-dodecahedron-motion-contact-sheet.png`
- `output/inspection.json`
- `output/video-inspection-preview.json`
- `output/wireframe-rhombic-dodecahedron-014-aligned-preview.mp4`

## 高清输出

- `output/video-inspection-hd.json`
- `output/rhombic-dodecahedron-motion-contact-sheet-hd.png`
- `output/wireframe-rhombic-dodecahedron-014-aligned-hd-720x1280.mp4`
- `output/video-inspection-hd60.json`
- `output/rhombic-dodecahedron-motion-contact-sheet-hd60.png`
- `output/wireframe-rhombic-dodecahedron-014-aligned-hd60-720x1280.mp4`

视频包含两整圈，但最后一帧停在闭合姿态前一个角步；未编码的下一帧才与首帧严格一致，因此循环点没有重复首帧造成的停顿。
