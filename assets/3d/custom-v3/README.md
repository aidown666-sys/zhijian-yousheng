# 本地细化版 V3

完全使用本机 Blender，未调用云端生成服务。用户已因费用选择本地优化；后续不应自行提交云端生成或付费任务。

新增：翻领/口袋通过躯干表面的射线检测重新贴合；裤腿轻微放宽；身体和面部表面细分；球形发髻替换为头皮和卷绕发束几何，合并成一个蒙皮网格减少网页绘制开销。保留 114 根骨骼、30 个主要手指关节，导出 FBX 内含贴图。V3 不含测试动画，网页仍由动作数据驱动。

必须明确的质量限制：脸部仍基于底模和 V2 的照片投射，眼睑/嘴部几何尚不能精确匹配参考脸；发际线及颈部有接缝，发丝是程序化几何，领口/翻领的剪裁仍不够真实。近景图会暴露这些问题。V3 是几何细化进展，不是高保真人物完成稿。

源文件 ReferenceWoman_LocalRefined.blend，导出 ReferenceWoman_LocalRefined.fbx；底模版权许可见 BASE_MODEL_LICENSE.txt，来源见 ../valid/SOURCE.json。制作脚本 tools/refine_avatar_local.py；检查 tools/verify_custom_fbx_v3.py。对照图和近景保存在 outputs/reference-v3/。
