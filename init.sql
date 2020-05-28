INSERT INTO `django_celery_beat_periodictask` (`name`, `task`, `enabled`, `args`, `kwargs`, `description`, `crontab_id`) VALUES ('minion状态检测入库','minion状态检测入库',1,'[]','{}','内置定时更新minion列表',1),('saltkey状态检测入库','saltkey状态检测入库',1,'[]','{}','内置定时更新saltkey信息表',1);

UPDATE `django_celery_beat_periodictask` SET enabled=0 WHERE name='celery.backend_cleanup';

INSERT INTO `xpgg_oms_myuser` VALUES (1,'pbkdf2_sha256$150000$navx9Mdvik6t$JyOg+FmO7x4PqzKnkgdrYztY9N1+4eMtM4Y+c/YVg2Q=','2020-04-13 15:15:50.693958',1,'admin','','','admin@qq.com',1,1,'2019-01-10 17:57:00.000000','avatar/default.png');

INSERT INTO `xpgg_oms_routes` VALUES 
(1,60,'Saltstack','/saltstack','/layout/Layout','/saltstack/minion-table',1,0,'Saltstack','saltstack',NULL,NULL,NULL,NULL,'2019-05-31 16:14:55.644873',NULL),
(2,70,'SaltMinionTable','minion-table','/views/saltstack/MinionTable',NULL,NULL,0,'Minion管理',NULL,NULL,NULL,NULL,NULL,'2019-05-31 16:15:26.071196',1),
(3,80,'SaltKeyTable','saltkey-table','/views/saltstack/SaltKeyTable',NULL,NULL,0,'SaltKey管理',NULL,NULL,NULL,NULL,NULL,'2019-05-31 16:17:29.707221',1),
(4,90,'SaltCmdTable','saltcmd-table','/views/saltstack/SaltCmdTable',NULL,NULL,0,'Salt命令集',NULL,NULL,NULL,NULL,NULL,'2019-05-31 16:17:56.288379',1),
(5,100,'SaltExe','saltexe','/views/saltstack/SaltExe',NULL,NULL,0,'Salt命令执行',NULL,NULL,NULL,NULL,NULL,'2019-05-31 16:18:30.451386',1),
(6,110,'SaltTool','saltool','/views/saltstack/SaltTool',NULL,NULL,0,'Salt快捷工具',NULL,NULL,NULL,NULL,NULL,'2019-05-31 16:18:53.025918',1),
(7,130,'Release','/release','/layout/Layout','/release/release-table',1,0,'发布系统','release',NULL,NULL,NULL,NULL,'2019-05-31 16:20:29.405541',NULL),
(8,140,'ReleaseTable','release-table','/views/release/ReleaseTable',NULL,NULL,0,'应用发布',NULL,NULL,NULL,NULL,NULL,'2019-05-31 16:21:34.250402',7),
(9,150,'ReleaseGroupTable','releasegroup-table','/views/release/ReleaseGroupTable',NULL,NULL,0,'应用发布组',NULL,NULL,NULL,NULL,NULL,'2019-05-31 16:25:13.831635',7),
(10,160,'ReleaseAuthTable','releaseauth-table','/views/release/ReleaseAuthTable',NULL,NULL,0,'应用授权',NULL,NULL,NULL,NULL,NULL,'2019-05-31 16:25:50.286667',7),
(11,155,'ReleaseGroupMemberTable','releasemember-table/:id/:app_group_name','/views/release/ReleaseGroupMemberTable',NULL,NULL,1,'组成员发布',NULL,NULL,NULL,NULL,'/release/releasegroup-table','2019-06-21 16:56:27.655857',7),
(12,1700,'Permission','/permission','/layout/Layou','/permission/role',1,0,'授权管理','lock',NULL,NULL,NULL,NULL,'2019-06-13 15:18:38.429113',NULL),
(13,1710,'RolePermission','role','/views/permission/role',NULL,NULL,0,'角色权限',NULL,NULL,NULL,NULL,NULL,'2019-06-13 15:19:25.710094',12),
(14,9500,NULL,'external-link','/layout/Layout',NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,'2019-06-13 15:21:08.748470',NULL),
(15,9550,NULL,'https://github.com/xiaopanggege/xpgg_pro',NULL,NULL,NULL,0,'External Link','link',NULL,NULL,NULL,NULL,'2019-06-13 15:21:44.694702',14),
(16,9000,'System','/system','/layout/Layout','/system/user',1,0,'系统管理','setting',NULL,NULL,NULL,NULL,'2019-07-22 11:20:46.183161',NULL),
(17,9100,'UserControl','user','/views/system/UserControl',NULL,NULL,0,'用户管理',NULL,NULL,NULL,NULL,NULL,'2019-07-22 11:21:54.770716',16),
(18,1600,'Task','/task','/layout/Layout','/task/task-table',1,0,'任务调度','crontab',NULL,NULL,NULL,NULL,'2019-07-31 11:20:22.388227',NULL),
(19,1610,'TaskTable','task-table','/views/task/TaskTable',NULL,NULL,0,'任务列表',NULL,NULL,NULL,NULL,NULL,'2019-07-31 11:21:22.225965',18),
(20,1620,'TaskLog','task-log','/views/task/TaskLog',NULL,NULL,0,'任务日志',NULL,NULL,NULL,NULL,NULL,'2019-07-31 11:22:14.042590',18),
(21,1630,'TaskTime','task-time','/views/task/TaskTime/index','/task/task-time/task-clocked',1,0,'任务时间',NULL,NULL,NULL,NULL,NULL,'2019-08-19 14:40:39.925337',18),
(22,1632,'TaskClocked','task-clocked','/views/task/TaskTime/TaskClocked',NULL,NULL,0,'Clocked',NULL,NULL,NULL,NULL,NULL,'2019-08-19 14:47:57.100030',21),
(23,1634,'TaskCrontab','task-crontab','/views/task/TaskTime/TaskCrontab',NULL,NULL,0,'Crontabs',NULL,NULL,NULL,NULL,NULL,'2019-08-19 14:48:37.735877',21),
(24,1636,'TaskInterval','task-interval','/views/task/TaskTime/TaskInterval',NULL,NULL,0,'Intervals',NULL,NULL,NULL,NULL,NULL,'2019-08-19 14:49:06.384499',21),
(25,115,'FileServer','fileserver','/views/saltstack/FileServer',NULL,NULL,0,'文件服务',NULL,NULL,NULL,NULL,NULL,'2020-01-02 15:49:24.465540',6);
