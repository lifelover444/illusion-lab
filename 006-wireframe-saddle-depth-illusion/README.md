# Wireframe Saddle Depth Illusion

一个用 Blender 生成的发光鞍形粒子表面旋转错觉实验。主体是双曲抛物面：左上与右下区域抬起，右上与左下区域压下；不使用实体面，改用密集彩色粒子和圆角外轮廓来暗示表面。旋转时，观众会在“中心凸出”和“中心凹入”之间重排深度关系。

## 文件结构

```text
006-wireframe-saddle-depth-illusion/
├─ scripts/
│  ├─ create_scene.py       # Blender 场景生成与渲染脚本
│  ├─ saddle-config.json    # 几何、相机、运动、输出规格
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
npm run scene:006
```

渲染低清预览：

```powershell
npm run render:006:preview
```

渲染竖屏最终版：

```powershell
npm run render:006:final
```

## 错觉设计

- 使用双曲抛物面粒子云，而不是实体面。
- 左上/右下角抬起，右上/左下角压下，形成凹凸可反转的鞍形。
- 约 11000 个柔和发光粒子按鞍面采样，边缘粒子更密，内部粒子更细。
- 圆角外轮廓承担主体结构，不再使用中间高亮流线，减少固定旋转方向线索。
- 正交相机轻微仰视，扶住更容易被替换掉的仰视/顺时针解释。
- 24 秒匀速旋转两圈，首尾姿态闭合，适合循环预览。
- 粒子颜色改成中性随机分布，不再按模型高度或角度形成可追踪梯度。
