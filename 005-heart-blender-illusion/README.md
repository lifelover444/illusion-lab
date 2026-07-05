# Heart Blender Illusion

005 是一个 Blender 双稳态旋转错觉实验。当前主体是发光莫比乌斯心形环：一条半透明丝带沿心形中心线闭合，并在完整路径上完成 180 度莫比乌斯扭转。

这个实验不使用剪影，也不做实心水晶心。错觉目标来自连续丝带运动、正交相机、正反面一致材质和弱深度线索。同一段绕竖直轴的线性旋转，应能被观看者合理感知为顺时针或逆时针。

## 命令

```powershell
npm run build:005
npm run test:005
npm run scene:005
npm run render:005:preview
npm run render:005:final
```

如果系统 PATH 中没有 `blender`，先设置 `BLENDER_BIN`：

```powershell
$env:BLENDER_BIN = "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
```

## 文件结构

```text
005-heart-blender-illusion/
├─ scripts/
│  ├─ create_scene.py              # 程序化 Blender 场景生成脚本
│  ├─ heart-illusion-config.json   # 渲染、几何、材质、相机、运动配置
│  └─ run-blender.mjs              # scene / preview / final 命令入口
├─ src/
│  └─ heartIllusionPlan.ts         # 可测试的错觉约束
├─ tests/
│  └─ heartIllusionPlan.test.ts
├─ package.json
├─ tsconfig.json
└─ vitest.config.ts
```

## 视觉设计

- 粉色 / 洋红色半透明莫比乌斯丝带面。
- 丝带边界使用更亮的发光曲线。
- 正交相机从负 `Y` 方向看向模型。
- 模型绕竖直 `Z` 轴匀速线性旋转。
- 深色背景，不使用地面和固定投影。
- 不使用透视相机、非对称纹理、玻璃折射或单侧高光。

## 视觉验收帧

重点检查这些旋转相位：

- `0°`：清晰正面心形。
- `90°`：被压缩但仍连续的扭转丝带。
- `180°`：心形以相近强度重新出现。
- `270°`：第二个压缩侧面阶段，仍然不暴露唯一旋转方向。

## 输出

场景命令会生成：

```text
005-heart-blender-illusion/output/heart-mobius-illusion.blend
```

预览渲染会生成：

```text
005-heart-blender-illusion/output/heart-mobius-illusion-preview.mp4
```

最终渲染会生成：

```text
005-heart-blender-illusion/output/heart-mobius-illusion.mp4
```
