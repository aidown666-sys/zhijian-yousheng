# 3D 资产与动作数据

FBX、Blend、GLB、VRM 和指定动作文件使用 Git LFS。克隆后执行 git lfs pull；未拉取的文本指针不能作为模型加载。

- 默认运行模型：assets/3d/user/SignHuman_CleanHands.glb。
- 优化源文件：assets/3d/user/source/SignHuman_CleanHands.blend 和同名 FBX。
- 原始备份：source/SignHuman_Final.fbx。
- 原手网格权重修复对照：SignHuman_HandsOptimized.glb 及 source 内同名 FBX/Blend。
- 手部校准：standard-hand-alignment.json，修改后同步更新。
- 大文件大小及 SHA-256：assets/MANIFEST.json。

当前人物脚本默认使用仓库内 source 目录，可用 SIGNHUMAN_SOURCE_DIR、SIGNHUMAN_WORK_DIR 覆盖。需要 Blender 自带 Python（bpy），普通 Python 不可直接执行。

```powershell
& '你的Blender目录\blender.exe' --background --python tools/repair_user_hands.py
& '你的Blender目录\blender.exe' --background --python tools/replace_with_donor_hands.py
& '你的Blender目录\blender.exe' --background --python tools/verify_clean_hands.py
```

脚本更新派生 GLB 和工作目录 FBX/Blend，运行前提交修改。启动项目无需重新建模。

本私有研究备份保存 data/lmdb/dev/CSL-Daily_reopt_dev.lmdb/data.mdb 和 data/sign_dictionary/csl_iso.dev，不包含训练集和推理模型。来源许可见 THIRD_PARTY_NOTICES.md，不代表可公开再分发的数据集。

LMDB SHA-256 为 c01bded1a737ba0405d7deedd13de3c6d8173584daadc47682b83449b93bd6d5。执行 python tools/verify_asset_manifest.py 核对可信文件，不解码陌生 pickle。
