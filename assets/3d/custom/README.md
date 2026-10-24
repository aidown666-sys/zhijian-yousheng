# 参考图女性：完整骨骼原型

这是对用户多视角参考图的定制尝试，不是多视角三维重建或与照片精确一致的模型。

- ReferenceWoman_Prototype.fbx：全身网格、蒙皮、身体及手指骨骼、内嵌贴图、关节检查动画。
- ReferenceWoman_Prototype.blend：可编辑 Blender 源文件，包含摄像机和灯光。
- CustomAvatar_BaseColor.png：UV 烘焙颜色贴图。
- reference-sheet.png：用户提供的参考图，供进一步人工建模。
- BASE_MODEL_LICENSE.txt：底模的 MIT 版权及许可；分发衍生模型时应保留。

底模来自 VALID 的 Asian_F_1_Busi，固定来源与哈希见 ../valid/SOURCE.json。现有拓扑、人体比例、头部网格及权重主要继承底模；本次调整为衣服改色、正面参考照片投射与烘焙、新增绑定头骨的几何发髻。没有精细重建参考图的脸型、翻领、鞋型或面部表情系统。正面图像投射存在接缝，侧面相似度不足，衣服不是参考图的精确剪裁。请勿把首版称为照片级或正式生产完成稿。

Rig_Check_Not_Sign_Language 动画仅检查关节运动，不代表任何手语词句。手语动作仍由网页从样本数据驱动，需校准掌心朝向、手部接触和关节约束，并由手语人员审核。

制作脚本：tools/build_reference_avatar.py；重导入检查：tools/verify_custom_fbx.py。输出预览和报告：outputs/custom-avatar/。Blender 5.4.0 Alpha 后台生成；已通过 FBX 结构检查不等于 Blender 源文件或其他软件版本完全兼容。
