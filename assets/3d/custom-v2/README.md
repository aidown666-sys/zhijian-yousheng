# 对齐修订版

相较旧版，按参考图重新标定正面眼睛、嘴、下巴以及侧面眼睛、鼻尖、嘴的位置。正面投射坐标：眼睛高度 162px → 1.594m、嘴高度约 212px → 1.532m；侧面按眼睛 441px、鼻尖约 1027px 标定。面部、眼球、牙齿使用统一烘焙，避免旧版不同纹理叠加。正/侧照片混合并过滤灰色背景，侧面仍有融合与肤色差异。

保留 VALID 底模拓扑、权重、骨架，修改下颌和腰部轮廓；增加独立翻领、口袋翻盖、纽扣及发髻几何，调整衣服、鞋子颜色，整体约 165cm。FBX 使用 T-pose 绑定，Blender 展示保存为 A-pose。测试动画只用于关节检查，不是标准手语。

这仍是基于现有底模的人工规则改制，不是从三视图精确重建。头部大部分几何、服装拓扑和鞋型仍来自底模；发丝、侧脸、布料结构、表情系统和局部接缝尚未完成精修。对照图用于展示实际差距，不代表已经达到参考图一致性。

文件：ReferenceWoman_Aligned.fbx、ReferenceWoman_Aligned.blend、CustomAvatar_BaseColor.png；原图 reference-sheet.png，底模 MIT 许可 BASE_MODEL_LICENSE.txt 必须保留。底模来源和哈希见 ../valid/SOURCE.json。脚本 tools/build_reference_avatar_v2.py；检查 tools/verify_custom_fbx_v2.py；检查报告和三视图对照见 outputs/reference-v2/。
