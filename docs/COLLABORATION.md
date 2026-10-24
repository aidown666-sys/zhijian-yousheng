# 私有仓库访问

仓库地址：https://github.com/aidown666-sys/zhijian-yousheng 。仅持有链接不能访问私有内容。

## 邀请他人

1. 请对方提供 GitHub 用户名，没有账号时先注册。
2. 仓库所有者打开仓库的 **Settings → Collaborators → Add people**。
3. 搜索对方用户名或邮箱，核对账号后发送邀请。
4. 对方登录 GitHub 并接受邀请后，即可浏览、克隆仓库和拉取 Git LFS 资产。

个人账号的私有仓库协作者具有读写权限，不是只读访客。若需要细分 Read、Write 等角色，可使用组织仓库；仅演示项目效果时也可以单独分享演示材料，无需给予代码访问权限。

## 对方在本地运行

安装 Git、Git LFS、Python 3.12，使用已获邀请的 GitHub 账号完成 Git 认证，然后执行：

```powershell
git lfs install
git clone https://github.com/aidown666-sys/zhijian-yousheng.git
cd zhijian-yousheng
git lfs pull
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
.\start.cmd
```

私有仓库访问权不会自动授予第三方资产的商业或公开再分发许可；各项来源见 THIRD_PARTY_NOTICES.md。

官方说明：[邀请协作者](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)、[个人仓库权限](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)。
