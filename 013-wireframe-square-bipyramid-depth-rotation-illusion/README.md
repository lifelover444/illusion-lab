# 冰晶星尘四角双锥深度旋转错觉

一个使用 Blender 脚本生成的完整四角双锥旋转错觉。四个腰部顶点组成清晰发亮的正方形，上下尖端与腰部中心共轴，八个三角面共同构成上下对称的单一模型。

外观参考项目附带的视觉样图：纯黑背景、冷白冰晶棱线、少量青蓝紫粉虹彩、极淡深蓝透明面，以及密集细碎的表面星尘。前后棱线和前后颗粒保持近似等亮，不设置灯光、阴影、折射或方向性装饰，让同一段刚体旋转可以被感知为顺时针或逆时针。

## 技术与结构

项目沿用 008 的独立 Blender 管线：

```text
scripts/create_scene.py                 # 场景、材质、粒子、动画、静帧与接触表
scripts/square-bipyramid-config.json    # 几何、质感、镜头、循环和输出参数
scripts/run-blender.mjs                 # Blender 命令入口
src/squareBipyramidGeometry.ts          # 可测试的双锥几何、投影和循环数学
tests/squareBipyramidGeometry.test.ts
scene/                                  # 生成的 .blend，不提交
output/                                 # 静帧、接触表与 MP4，不提交
```

默认场景包含：

- 6 个唯一顶点、8 个三角面和 12 条结构棱线；
- 4 条清晰发亮的正方形腰线；
- 3200 个稀疏表面星尘和 760 个棱线冰晶；
- 1500 个分成背景、彩色和微光三层的内部太空尘粒，以 12 秒周期轻微旋转漂移和上下浮动；
- 极淡透明烟晶外壳；
- 无灯光、无地面、无阴影的正交相机画面；
- 12 秒一圈、24 秒两整圈的线性动画，第 1 帧与末帧像素一致，适合短视频平台循环播放。

## 命令

在仓库根目录运行：

```powershell
npm run test:013
npm run build:013
npm run scene:013
npm run render:013:stills
npm run render:013:preview
npm run render:013:final
```

默认 Blender 路径为：

```text
D:\software\Blender 4.5 LTS\blender.exe
```

可以通过 `BLENDER_EXE` 环境变量覆盖。

## 输出

- 静帧接触表：`output/stills/square-bipyramid-contact-sheet.png`
- 场景检查数据：`output/inspection.json`
- 低清预览：`360 × 640`、15 fps、24 秒
- 最终版：`720 × 1280`、30 fps、24 秒

先检查静帧接触表和低清预览，再执行最终渲染。
