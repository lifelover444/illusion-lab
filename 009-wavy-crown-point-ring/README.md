# 四波峰点云环

一个由冷白色发光点组成的四波峰薄环带旋转错觉。主体保持清楚的中央圆孔和极薄厚度，整个环带沿圆周缓慢上下起伏四次。正交相机、均匀点色和无阴影环境会削弱前后关系，使同一段旋转可能被感知为顺时针或逆时针。

## 形体

- 基础形体是一片有宽度的薄圆环，不是圆管、麻花或四片花瓣。
- 圆周上有四个宽波峰与四个宽波谷。
- 波峰只改变高度，不改变环带宽度和中央孔大小。
- 表面使用约 5440 个均匀扰动的微小冷白发光点，不绘制连续网格线。
- 不使用彩色点、阴影或方向性条带。

## 命令

```powershell
npm run scene:009
npm run render:009:stills
npm run render:009:preview
npm run render:009:final
```

默认使用 `D:\software\Blender 4.5 LTS\blender.exe`。如果 Blender 安装在其他位置，请通过 `BLENDER_EXE` 环境变量指定。

## 文件结构

```text
009-wavy-crown-point-ring/
├─ scripts/
│  ├─ create_scene.py
│  ├─ run-blender.mjs
│  └─ wavy-crown-config.json
├─ src/wavyCrownGeometry.ts
├─ tests/wavyCrownGeometry.test.ts
├─ scene/
└─ output/
```
