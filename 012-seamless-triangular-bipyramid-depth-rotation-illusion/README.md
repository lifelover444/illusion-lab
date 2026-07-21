# 二向色玻璃三角双锥深度旋转错觉

一颗由五个唯一顶点和六个三角面构成的完整三角双锥。当前版本不再使用白色点云，而是把六个面合并为一个闭合玻璃外壳，并共用同一个低饱和二向色材质。

玻璃主体使用深蓝烟色透射，连续的物体空间极光色场与视角 Fresnel 共同生成深蓝、青蓝、紫罗兰和少量洋红变化。六盏成对面积灯只提供柔和辅助反射，不绘制棱线、中部腰线或额外装饰。正交镜头和透明前后面仍保留一定的深度重新解释空间，但本版优先保证整体观赏性。

## 几何与动画

- 中部外接圆半径 `R = 1.0`，三个中部顶点位于 `z = 0` 并相隔 `120°`。
- 上下尖端位于 `z = ±sqrt(2)`，初始相位为 `30°`。
- 渲染场景只有一个五顶点、六三角面的闭合 mesh 和一个玻璃材质，点云数量为零。
- 三组成对面积灯围绕主体对称布置，共六盏；没有 HDRI、地面或环境物体。
- 每圈 `5.4` 秒，总时长 `10.8` 秒，恰好两圈。
- 动画只作用于一个刚体旋转 Rig；循环后的下一帧与首帧角度一致。

## 视觉设计

- 深蓝黑背景和大面积留白。
- 色域限制为深蓝、青蓝、紫罗兰和克制的洋红，不使用完整彩虹。
- 主色由连续物体空间色场产生，不依赖把灯箱形状直接反射到切面上。
- 玻璃使用透射、低密度体积吸收、薄膜参数和低强度自发光共同维持黑背景可读性。
- 不画连续棱线、中部三角腰线、彩色描边或内部几何。
- Bloom 只柔化最亮区域，不产生发光外轮廓。

## 命令

在仓库根目录运行：

```powershell
npm run test:012
npm run build:012
npm run scene:012
npm run render:012:stills
npm run render:012:preview
npm run render:012:final
```

`render:012:stills` 生成 `0°、30°、60°、90°、120°、180°、240°、300°、360°` 九个关键相位和横向接触表。预览为 `360 × 640`、15 fps、10.8 秒；最终配置为 `720 × 1280`、30 fps、10.8 秒。

未经用户检查新的接触表和低清预览，不执行 `render:012:final`。

默认 Blender 路径为 `D:\software\Blender 4.5 LTS\blender.exe`，可通过 `BLENDER_EXE` 环境变量覆盖。

## 本地结构

```text
src/triangularBipyramidGeometry.ts    # 可测试的几何、投影和循环逻辑
tests/triangularBipyramidGeometry.test.ts
scripts/create_scene.py               # 统一玻璃外壳、材质、灯光和渲染生成器
scripts/run-blender.mjs               # Blender 命令入口
scripts/triangular-bipyramid-config.json
scene/                                # 生成的 .blend 文件，不提交
output/                               # 静帧、接触表和视频，不提交
```
