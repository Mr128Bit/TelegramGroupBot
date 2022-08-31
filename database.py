import aiosqlite
import sqlite3
import permissions as pm

def setup_database(database):
    querys = ["CREATE TABLE IF NOT EXISTS groups (gid int PRIMARY KEY, pro bool, auto_raid_detect bool, raid_treshold int)",
    """
CREATE TABLE IF NOT EXISTS logging (
  gid int,
  log_channel_id int, 
  logging_active bool, 
  log_commands bool,
  log_raid_status bool,
  log_join bool, 
  log_leave bool,
  FOREIGN KEY (gid) REFERENCES groups(gid)
)
    """,
    """
CREATE TABLE IF NOT EXISTS staff (
  gid int, 
  uid int, 
  can_privilege_user bool, 
  can_kick bool, 
  can_mute bool, 
  can_delete bool, 
  can_modify_bot bool,
  UNIQUE(gid,uid)
)
    """,
    """
CREATE TABLE IF NOT EXISTS msg_config (
    gid int,
    captcha_active bool,    
    captcha_type int,
    captcha_punishment int,
    captcha_punishment_time int,
    captcha_msg_text text,
    captcha_button_text text,
    welcome_active bool,
    welcome_msg_text text,
    FOREIGN KEY (gid) REFERENCES groups(gid)
)
    """,
    """
CREATE TABLE IF NOT EXISTS templates_en (
    captcha_template varchar(4000),
    button_text_template varchar(200),
    welcome_template varchar(4000)
)   
    """

     ]
    con = sqlite3.connect(database)
    cur = con.cursor()
    for q in querys:
        cur.execute(q)
    con.commit() 
    con.close()


async def save_conf(CONFIG, database):
    async with aiosqlite.connect(database) as db:
        for group in CONFIG["groups"]:
            print(group)
            gconf = CONFIG["groups"][group]
            if gconf["bot_kicked"]:
                delete_qry = "DELETE FROM groups WHERE gid = " + str(group)
                await db.execute(delete_qry)
            if gconf["updated"]:
                update_group_qry = "UPDATE groups SET pro = ?, auto_raid_detect = ?, raid_treshold = ? WHERE gid = ?"
                await db.execute(update_group_qry, (gconf["is_pro"], gconf["auto_raid_detection"], gconf["auto_raid_treshold"], group))
                update_log_qry = "UPDATE logging SET log_channel_id = ?, logging_active = ?, log_commands = ?, log_raid_status = ?, log_join = ?, log_leave = ? WHERE gid = ?"
                await db.execute(update_log_qry, (gconf["log_channel"], gconf["log_active"], gconf["log_commands"], gconf["log_raid_status"], gconf["log_join"], gconf["log_leave"], group))
                update_msg_config_qry = "UPDATE msg_config SET captcha_active = ?, captcha_type = ?, captcha_punishment = ?, captcha_punishment_time = ?, captcha_msg_text = ?, captcha_button_text = ?, welcome_active = ?, welcome_msg_text = ? WHERE gid = ?"
                await db.execute(update_msg_config_qry, (gconf["captcha_active"], gconf["captcha_type"], gconf["captcha_punishment"], gconf["captcha_punishment_time"], gconf["captcha_text"], gconf["captcha_button_text"], gconf["welcome_active"], gconf["welcome_text"], group))
                gconf["updated"] = False
            elif gconf["created"]:
                insert_group_qry = "INSERT INTO groups (gid, pro, auto_raid_detect, raid_treshold) VALUES (?,?,?,?)"
                await db.execute(insert_group_qry, (group, gconf["is_pro"], gconf["auto_raid_detection"], gconf["auto_raid_treshold"]))
                insert_log_qry = "INSERT INTO logging (gid, log_channel_id, logging_active, log_commands, log_raid_status, log_join, log_leave) VALUES (?,?,?,?,?,?,?)"
                #logging.error(str(group) + " "  + str(gconf["log_channel"]) + " " + str(gconf["log_active"]) + " " + str(gconf["log_commands"])  + " " + str(gconf["log_raid_status"]) + " " + str(gconf["log_join"]) + " " + str(gconf["log_leave"]))
                await db.execute(insert_log_qry, (group, gconf["log_channel"], gconf["log_active"], gconf["log_commands"], gconf["log_raid_status"], gconf["log_join"], gconf["log_leave"]))
                insert_msg_config_qry = "INSERT INTO msg_config VALUES(?,?,?,?,?,?,?,?,?)"
                await db.execute(insert_msg_config_qry, (group, gconf["captcha_active"], gconf["captcha_type"].value, gconf["captcha_punishment"], gconf["captcha_punishment_time"], gconf["captcha_text"], gconf["captcha_button_text"], gconf["welcome_active"], gconf["welcome_text"]))
                gconf["created"] = False
            if gconf["privileges_updated"]:
               # res = await db.execute("SELECT * FROM staff WHERE gid = '"  + str(group) + "'")
                async with db.execute("SELECT * FROM staff WHERE gid = '"  + str(group) + "'") as res:
                    async for r in res:
                        if r[1] not in gconf["privileged"]:
                            del_qry = "DELETE FROM staff WHERE uid = ? AND gid = ?"
                            await db.execute(del_qry, (r[1], r[0]))
                        else:
                            update_qry = "UPDATE staff SET can_privilege_user = ?, can_kick = ?, can_mute = ?, can_delete = ?, can_modify_bot = ? WHERE gid = ? AND uid = ?"
                            privileged = gconf["privileged"]
                            can_privilege_user = False
                            can_kick = False
                            can_mute = False
                            can_delete = False
                            can_modify_bot = False

                            if pm.AdminPermission.CAN_PRIVILEGE_USER in privileged[r[1]]:
                                can_privilege_user = True
                            if pm.AdminPermission.CAN_KICK in privileged[r[1]]:
                                can_kick = True
                            if pm.AdminPermission.CAN_MUTE in privileged[r[1]]:
                                can_mute = True
                            if pm.AdminPermission.CAN_DELETE in privileged[r[1]]:
                                can_delete = True
                            if pm.AdminPermission.CAN_MODIFY_BOT in privileged[r[1]]:
                                can_modify_bot = True

                            for usr in privileged:
                                await db.execute(update_qry,(can_privilege_user, can_kick, can_mute, can_delete, can_modify_bot, group, usr))
            
                for user in gconf["privileged"]:
                    privileged = CONFIG["groups"][group]["privileged"]
                    qry = "INSERT OR IGNORE INTO staff VALUES(?,?,?,?,?,?,?)"
                    can_privilege_user = False
                    can_kick = False
                    can_mute = False
                    can_delete = False
                    can_modify_bot = False

                    if pm.AdminPermission.CAN_PRIVILEGE_USER in privileged[user]:
                        can_privilege_user = True
                    if pm.AdminPermission.CAN_KICK in privileged[user]:
                        can_kick = True
                    if pm.AdminPermission.CAN_MUTE in privileged[user]:
                        can_mute = True
                    if pm.AdminPermission.CAN_DELETE in privileged[user]:
                        can_delete = True
                    if pm.AdminPermission.CAN_MODIFY_BOT in privileged[user]:
                        can_modify_bot = True

                    await db.execute(qry,(group,user,can_privilege_user, can_kick, can_mute, can_delete, can_modify_bot))
            gconf["privileges_updated"] = False
        await db.commit()

def get_conf_from_db(database):
    CONFIG = {}
    with sqlite3.connect(database) as con:
        cur = con.cursor()
        qry = "SELECT * FROM groups JOIN logging ON groups.gid=logging.gid JOIN msg_config ON groups.gid = msg_config.gid"
        result = cur.execute(qry)
        CONFIG["groups"] = {}
        for r in result:
            print(r)
            CONFIG["groups"][r[0]] = {
                "is_pro" : r[1],
                "auto_raid_detection" : r[2],
                "auto_raid_treshold" : r[3],
                "log_channel" : r[5],
                "log_active" : r[6],
                "log_commands" : r[7],
                "log_raid_status" : r[8],
                "log_join" : r[9],
                "log_leave" : r[10],
                "captcha_active": r[12],
                "captcha_type": r[13],
                "captcha_punishment": r[14],
                "captcha_punishment_time": r[15],
                "captcha_text": r[16],
                "captcha_button_text":r[17],
                "welcome_active": r[18],
                "welcome_text": r[19],
                "updated" : False,
                "created" : False,
                "privileges_updated" : False,
                "privileged" : {},
                "bot_kicked" : False
            }  
        
            qry = "SELECT * FROM staff WHERE gid = " + str(r[0])
            result = cur.execute(qry)

            for r in result:
                permissions = []
                if r[2]:
                    permissions.append(pm.AdminPermission.CAN_PRIVILEGE_USER)
                if r[3]:
                    permissions.append(pm.AdminPermission.CAN_KICK)
                if r[4]:
                    permissions.append(pm.AdminPermission.CAN_MUTE)
                if r[5]:
                    permissions.append(pm.AdminPermission.CAN_DELETE)
                if r[6]:
                    permissions.append(pm.AdminPermission.CAN_MODIFY_BOT)
                CONFIG["groups"][r[0]]["privileged"][r[1]] = permissions

    return CONFIG