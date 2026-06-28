# 001 极光丝带

这是一个 Three.js 视觉错觉实验，主体是一组像极光一样发光、流动的丝带形态。画面使用叠加发光材质、细微粒子场和固定中文文案，营造出“旋转方向可能被大脑重新解释”的效果。

页面文案：

> 视觉测试  
> 你能用意念改变它的旋转方向吗？

## 启动

从仓库根目录启动：

```powershell
npm run dev:001
```

也可以进入当前目录启动：

```powershell
npm run dev
```

## 构建和测试

```powershell
npm run build
npm run test
```

## 文件说明

- `src/main.ts`：创建并驱动 Three.js 场景。
- `src/ribbon.ts`：生成丝带曲面的几何数据。
- `tests/ribbon.test.ts`：验证几何数据数量和边界范围。
- `assets/screenshots/`：存放视觉检查截图。
- `aurora-ribbon-video/`：HyperFrames 视频导出工程，用于生成 35 秒循环视频。
