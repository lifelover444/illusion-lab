# Pink Heart Point Cloud

一个用 Blender 生成的粉色低密度心形点阵云旋转错觉实验。目标是让心形保持清晰，同时减少实体表面、强光照、透视和阴影带来的前后方向线索，让观众有机会反复感知顺时针或逆时针旋转。

## 文件结构

```text
005-pink-heart-point-cloud/
├─ scripts/
│  ├─ create_scene.py       # Blender 场景生成与渲染脚本
│  ├─ heart-config.json     # 点云、运动、相机、输出规格
│  └─ run-blender.mjs       # Node 包装脚本
├─ src/
│  └─ heartPointCloud.ts    # 可测试的心形点云生成逻辑
├─ tests/
│  └─ heartPointCloud.test.ts
├─ scene/                   # 本地生成的 .blend 文件
└─ output/                  # 本地生成的 MP4 文件
```

`scene/` 和 `output/` 是生成产物目录，默认不提交到 Git。运行命令后可以直接打开本地生成的 `.blend` 或预览视频。

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
npm run scene --workspace @illusion-lab/pink-heart-point-cloud
```

渲染低清预览：

```powershell
npm run render:preview --workspace @illusion-lab/pink-heart-point-cloud
```

渲染竖屏最终版：

```powershell
npm run render:final --workspace @illusion-lab/pink-heart-point-cloud
```

根目录快捷命令：

```powershell
npm run scene:005
npm run render:005:preview
npm run render:005:final
```

## 错觉设计

- 使用约 640 个粉色发光点，而不是实体心形表面。
- 点云深度较浅，避免稳定的前后遮挡判断。
- 使用正交相机和恒速旋转，不使用透视镜头。
- 默认不添加阴影；如果后续需要空间参照，只能加入极淡且相位联动的地面线索。
- 12 秒总时长，6 秒一圈，预览时能看到两次完整旋转。
