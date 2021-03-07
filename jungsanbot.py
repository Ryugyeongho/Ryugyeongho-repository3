# -*- coding: utf-8 -*- 

##################################### 서버용 V12 ##########################################
#########################################################################################
#########################################################################################
#########################################################################################
###### 개발환경 : python 3.7.3														######
######			discord = 1.0.1														######
######			discord.py = 1.6.0													######
###### 모듈설치 : pip install setuptools --upgrade									######
######			pip install discord													######
######			pip install discord.py[voice]										######
######			pip install pymongo													######
######			pip install PyGithub												######
#########################################################################################
#########################################################################################
#########################################################################################

import os
import sys
import asyncio
import discord
import datetime
import logging
from discord.ext import tasks, commands
from discord.ext.commands import CommandNotFound, MissingRequiredArgument
from io import StringIO
import aiohttp
from pymongo import MongoClient
import pymongo, ssl, traceback, random
from github import Github
import base64

log_stream = StringIO()    
logging.basicConfig(stream=log_stream, level=logging.WARNING)

##################### 로깅 ###########################
#ilsanglog = logging.getLogger('discord')
#ilsanglog.setLevel(level = logging.WARNING)
#handler = logging.FileHandler(filename = 'discord.log', encoding='utf-8',mode='a')
#handler.setFormatter(logging.Formatter('%(asctime)s: %(levelname)s: %(name)s: %(message)s'))
#ilsanglog.addHandler(handler)
#####################################################

access_token = os.environ["BOT_TOKEN"]
git_access_token = os.environ["GIT_TOKEN"]
git_access_repo = os.environ["GIT_REPO"]	
mongoDB_HOST = os.environ["MONGODB_HOST"]
user_ID = os.environ["USER_ID"]
user_PASSWORD = os.environ["USER_PW"]
time_Zone = os.environ["TIME_ZONE"]

g = Github(git_access_token)
repo = g.get_repo(git_access_repo)


def init():
	global commandSetting
	global basicSetting

	basicSetting = []
	commandSetting = []
	fc = []

	command_inidata = repo.get_contents("command.ini")
	file_data4 = base64.b64decode(command_inidata.content)
	file_data4 = file_data4.decode('utf-8')
	commandData = file_data4.split('\n')

	for i in range(commandData.count('\r')):
		commandData.remove('\r')

	del(commandData[0])
		
	############## 분배봇 초기 설정 리스트 #####################
	basicSetting.append(access_token)
	basicSetting.append(mongoDB_HOST)
	basicSetting.append(user_ID)
	basicSetting.append(user_PASSWORD)

	# basicSetting[0] = bot_token
	# basicSetting[1] = host
	# basicSetting[2] = user_ID
	# basicSetting[3] = user_PASSWORD
	# basicSetting[4] = backup_period
	# basicSetting[5] = checktime
	# basicSetting[6] = distributionchannel
	# basicSetting[7] = tax
	# basicSetting[8] = timezone

	############## 보탐봇 명령어 리스트 #####################
	for i in range(len(commandData)):
		tmp_command = commandData[i][(commandData[0].find("="))+2:].rstrip('\r')
		fc = tmp_command.split(', ')
		commandSetting.append(fc)
		fc = []

init()

def is_manager():
	async def pred(ctx : commands.Context) -> bool:
		user_info : dict = ctx.bot.db.jungsan.member.find_one({"_id":ctx.author.id})
		if not user_info:
			return False
		if "manager" in user_info["permissions"]:
			return True
		return False
	return commands.check(pred)

#서버(길드) 정보 
def get_guild_channel_info(bot):
	text_channel_name : list = []
	text_channel_id : list = []
	
	for guild in bot.guilds:
		for text_channel in guild.text_channels:
			text_channel_name.append(text_channel.name)
			text_channel_id.append(str(text_channel.id))

	return text_channel_name, text_channel_id

#detail embed
def get_detail_embed(info : dict = {}):
	# "_id" : int = 순번
	# "regist_ID" : str = 등록자ID
	# "regist" : str = 등록자 겜 ID
	# "getdate" : datetime = 등록날짜
	# "boss" : str = 보스명
	# "item" : str = 아이템명
	# "toggle" : str = 루팅자 게임 ID
	# "toggle_ID" : str = 루팅자ID
	# "itemstatus" : str = 아이템상태(미판매, 분배중, 분배완료)
	# "price" : int = 가격
	# "each_price" : int = 분배가격
	# "before_jungsan_ID" : list = 참석명단(분배전)
	# "after_jungsan_ID" : list = 참석명단(분배후)
	# "modifydate" : datetime = 수정날짜
	# "gulid_money_insert" : bool = 혈비등록여부
	# "bank_money_insert" : bool = 은행입금여부
	# "image_url":""

	embed = discord.Embed(
			title = "📜 등록 정보",
			description = "",
			color=0x00ff00
			)
	embed.add_field(name = "[ 순번 ]", value = f"```{info['_id']}```")
	embed.add_field(name = "[ 등록 ]", value = f"```{info['regist']}```")
	embed.add_field(name = "[ 일시 ]", value = f"```{info['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
	embed.add_field(name = "[ 보스 ]", value = f"```{info['boss']}```")
	embed.add_field(name = "[ 아이템 ]", value = f"```{info['item']}```")
	embed.add_field(name = "[ 루팅 ]", value = f"```{info['toggle']}```")
	embed.add_field(name = "[ 상태 ]", value = f"```{info['itemstatus']}```")
	embed.add_field(name = "[ 판매금 ]", value = f"```{info['price']}```")
	if info['before_jungsan_ID']:
		embed.add_field(name = "[ 정산전 ]", value = f"```{', '.join(info['before_jungsan_ID'])}```", inline = False)
	if info['after_jungsan_ID']:
		embed.add_field(name = "[ 정산후 ]", value = f"```{', '.join(info['after_jungsan_ID'])}```")
	if 'image_url' in info.keys():
		if info['image_url'] is not None:
			embed.set_image(url = info['image_url'])
	return embed

class IlsangDistributionBot(commands.AutoShardedBot):
	def __init__(self):
		self.cog_list : list = ["admin", "manage", "member", "bank"]
		self.db = None

		self.mongoDB_connect_info : dict = {
			"host" : basicSetting[1],
			"username" : basicSetting[2],
			"password" : basicSetting[3]
			}
			
		INTENTS = discord.Intents.all()

		super().__init__(command_prefix=[""], help_command=None, intents=INTENTS)

		# db 설정
		self.db = None
		try:
			self.db = MongoClient(ssl=True, ssl_cert_reqs=ssl.CERT_NONE, **self.mongoDB_connect_info)
			self.db.admin.command("ismaster") # 연결 완료되었는지 체크
			print(f"db 연결 완료. 아이디:{self.mongoDB_connect_info['username']}")
		except pymongo.errors.ServerSelectionTimeoutError:
			return print("db 연결 실패! host 리스트를 확인할 것.")
		except pymongo.errors.OperationFailure:
			return print("db 로그인 실패! username과 password를 확인할 것.")
		except:
			return print("db 연결 실패! 오류 발생:")

		guild_data : dict = self.db.jungsan.guild.find_one({"_id":"guild"})

		if not guild_data:
			init_guild_data : dict = {
				"guild_money":0,
				"back_up_period":14,
				"checktime":15,
				"distributionchannel":0,
				"tax":5
				}
			update_guild_data : dict = self.db.jungsan.guild.update_one({"_id":"guild"}, {"$set":init_guild_data}, upsert = True)

			basicSetting.append(init_guild_data['back_up_period'])
			basicSetting.append(init_guild_data['checktime'])
			basicSetting.append(init_guild_data['distributionchannel'])
			basicSetting.append(init_guild_data['tax'])			
		else:
			basicSetting.append(guild_data['back_up_period'])
			basicSetting.append(guild_data['checktime'])
			basicSetting.append(guild_data['distributionchannel'])
			basicSetting.append(guild_data['tax'])

		basicSetting.append(time_Zone)

		# basicSetting[4] = backup_period
		# basicSetting[5] = checktime
		# basicSetting[6] = distributionchannel		
		# basicSetting[7] = tax
		# basicSetting[8] = timezone			

		self.backup_data.start()

	def run(self):
		super().run(basicSetting[0], reconnect=True)

	@tasks.loop(hours=12.0)
	async def backup_data(self):
		await self.wait_until_ready()
		if basicSetting[6] != "" and basicSetting[6] != 0 :
			backup_date = datetime.datetime.now() - datetime.timedelta(days = int(basicSetting[4])) + datetime.timedelta(hours = int(basicSetting[8]))
			log_delete_date = datetime.datetime.now() - datetime.timedelta(days = int(30))
			
			jungsan_document :list = []
			delete_jungsan_id : list = []
			backup_jungsan_document : list = []
			total_save_money : int = 0
			cnt : int = 0

			jungsan_document = list(self.db.jungsan.jungsandata.find({"modifydate":{"$lt":backup_date}, "itemstatus":"분배중"}))

			for jungsan_data in jungsan_document:
				cnt += 1
				total_save_money += int(jungsan_data['each_price']*len(jungsan_data['before_jungsan_ID'])*(1-(basicSetting[7]/100)))
				delete_jungsan_id.append(jungsan_data['_id'])
				del jungsan_data['_id']
				jungsan_data["getdate"] = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
				backup_jungsan_document.append(jungsan_data)

			self.db.jungsan.guild_log.delete_many({'log_date':{"$lt":log_delete_date}})
			self.db.jungsan.jungsandata.delete_many({"$and": [{'modifydate':{"$lt":log_delete_date}}, {"itemstatus":"분배완료"}]})
			self.db.jungsan.jungsandata.delete_many({'_id':{'$in':delete_jungsan_id}})

			if len(backup_jungsan_document) > 0:
				tmp : list = list(map(str,delete_jungsan_id))
				self.db.backup.backupdata.insert_many(backup_jungsan_document)

				result_guild_update : dict = self.db.jungsan.guild.update_one({"_id":"guild"}, {"$inc":{"guild_money":total_save_money}}, upsert = True)
				total_guild_money : dict = self.db.jungsan.guild.find_one({"_id":"guild"})

				insert_log_data = {
							"in_out_check":True, # True : 입금, False : 출금
							"log_date":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])),
							"money":str(total_save_money),
							"member_list":[],
							"reason":"정산 자동 삭제 후 적립"
				}
				result_guild_log = self.db.jungsan.guild_log.insert_one(insert_log_data)

				embed = discord.Embed(
						title = f"💰  혈비 자동 적립 ({(datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))).strftime('%y-%m-%d %H:%M:%S')})",
						description = f"",
						color=0x00ff00
						)
				embed.add_field(name = f"**삭제순번**", value = f"**```fix\n{' '.join(tmp)}```**", inline = False)
				embed.add_field(name = f"**적립**", value = f"**```fix\n{total_save_money}```**")
				embed.add_field(name = f"**혈비**", value = f"**```fix\n{total_guild_money['guild_money']}```**")
				embed.set_footer(text = f"기간({basicSetting[4]}일) 경과로 인하여 총 {cnt}건 혈비 자동적립 완료\n(총 혈비 {total_guild_money['guild_money']})")

				await self.get_channel(int(basicSetting[6])).send(embed = embed)

	async def on_ready(self):
		print("Logged in as ") #화면에 봇의 아이디, 닉네임이 출력됩니다.
		print(self.user.name)
		print(self.user.id)
		print("===========")

		channel_name, channel_id = get_guild_channel_info(self)

		if str(basicSetting[6]) in channel_id:
			print(f"< 접속시간 [{(datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))).strftime('%y-%m-%d %H:%M:%S')}] >")
			print(f"< 텍스트채널 [{self.get_channel(int(basicSetting[6])).name}] 접속완료 >")
		else:
			basicSetting[6] = 0
			print(f"설정된 채널 값이 없거나 잘못 됐습니다. [{commandSetting[36][0]}] 명령어를 먼저 입력하여 사용해주시기 바랍니다.")
		
		await self.change_presence(status=discord.Status.dnd, activity=discord.Game(name=f"{commandSetting[39][0]}", type=1), afk = False)

	async def on_command_error(self, ctx : commands.Context, error : commands.CommandError):
		if isinstance(error, CommandNotFound):
			return
		elif isinstance(error, MissingRequiredArgument):
			return
		elif isinstance(error, discord.ext.commands.MissingPermissions):
			return await ctx.send(f"**[{ctx.message.content.split()[0]}]** 명령을 사용할 권한이 없습니다.!")
		elif isinstance(error, discord.ext.commands.CheckFailure):
			return await ctx.send(f"**[{ctx.message.content.split()[0]}]** 명령을 사용할 권한이 없습니다.!")
		raise error

	async def close(self):
		await super().close()
		print("일상분배봇 종료 완료.")

class settingCog(commands.Cog): 
	def __init__(self, bot):
		self.bot = bot

		self.member_db = self.bot.db.jungsan.member
		self.jungsan_db = self.bot.db.jungsan.jungsandata
		self.guild_db = self.bot.db.jungsan.guild
		self.guild_db_log = self.bot.db.jungsan.guild_log

	################ 채널등록 ################ 
	@commands.has_permissions(manage_guild=True)
	@commands.command(name=commandSetting[36][0], aliases=commandSetting[36][1:])
	async def join_channel(self, ctx, *, args : str = None):
		global basicSetting

		if basicSetting[6] == "" or basicSetting[6] == 0:
			channel = ctx.message.channel.id #메세지가 들어온 채널 ID

			print (f"[ {basicSetting[6]} ]")
			print (f"] {ctx.message.channel.name} [")

			basicSetting[6] = str(channel)

			result = self.guild_db.update_one({"_id":"guild"}, {"$set":{"distributionchannel":str(channel)}}, upsert = True)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 채널 등록 실패.")   

			await ctx.send(f"< 텍스트채널 [{ctx.message.channel.name}] 접속완료 >", tts=False)
			
			print(f"< 텍스트채널 [ {self.bot.get_channel(int(basicSetting[6])).name} ] 접속완료>")
		else:
			curr_guild_info = None
			for guild in self.bot.guilds:
				for text_channel in guild.text_channels:
					if basicSetting[6] == str(text_channel.id):
						curr_guild_info = guild

			emoji_list : list = ["⭕", "❌"]
			guild_error_message = await ctx.send(f"이미 **[{curr_guild_info.name}]** 서버 **[{curr_guild_info.get_channel(int(basicSetting[6])).name}]** 채널이 명령어 채널로 설정되어 있습니다.\n해당 채널로 명령어 채널을 변경 하시려면 ⭕ 그대로 사용하시려면 ❌ 를 눌러주세요.\n({basicSetting[5]}초 이내 미입력시 기존 설정 그대로 설정됩니다.)", tts=False)

			for emoji in emoji_list:
				await guild_error_message.add_reaction(emoji)

			def reaction_check(reaction, user):
				return (reaction.message.id == guild_error_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)
			try:
				reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
			except asyncio.TimeoutError:
				return await ctx.send(f"시간이 초과됐습니다. **[{curr_guild_info.name}]** 서버 **[{curr_guild_info.get_channel(int(basicSetting[6])).name}]** 채널에서 사용해주세요!")
			
			if str(reaction) == "⭕":
				basicSetting[6] = str(ctx.message.channel.id)

				print ('[ ', basicSetting[6], ' ]')
				print ('] ', ctx.message.channel.name, ' [')
			
				result = self.guild_db.update_one({"_id":"guild"}, {"$set":{"distributionchannel":str(basicSetting[6])}}, upsert = True)
				if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
					return await ctx.send(f"{ctx.author.mention}, 채널 등록 실패.")

				return await ctx.send(f"명령어 채널이 **[{ctx.author.guild.name}]** 서버 **[{ctx.message.channel.name}]** 채널로 새로 설정되었습니다.")
			else:
				return await ctx.send(f"명령어 채널 설정이 취소되었습니다.\n**[{curr_guild_info.name}]** 서버 **[{curr_guild_info.get_channel(int(basicSetting[6])).name}]** 채널에서 사용해주세요!")

	################ 백업주기 설정 ################ 
	@is_manager()
	@commands.command(name=commandSetting[40][0], aliases=commandSetting[40][1:])
	async def set_backup_time(self, ctx, *, args : str = None):
		global basicSetting

		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[40][0]} [숫자]** 양식으로 등록 해주세요")
		
		try:
			args = int(args)
		except ValueError:
			return await ctx.send(f"**정산 내역 삭제 주기는 [숫자]** 로 입력 해주세요")

		basicSetting[4] = args
		result = self.guild_db.update_one({"_id":"guild"}, {"$set":{"back_up_period":args}}, upsert = True)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 정산 내역 삭제 주기 설정 실패.")   

		return  await ctx.send(f"정산 내역 삭제 주기를 **[{args}]**일로 설정 하였습니다.")

	################ 확인시간 설정 ################ 
	@is_manager()
	@commands.command(name=commandSetting[41][0], aliases=commandSetting[41][1:])
	async def set_check_time(self, ctx, *, args : str = None):
		global basicSetting

		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[41][0]} [숫자]** 양식으로 등록 해주세요")
		
		try:
			args = int(args)
		except ValueError:
			return await ctx.send(f"**이모지 확인 시간은 [숫자]** 로 입력 해주세요")

		basicSetting[5] = args
		result = self.guild_db.update_one({"_id":"guild"}, {"$set":{"checktime":args}}, upsert = True)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 이모지 확인 시간 설정 실패.")   

		return  await ctx.send(f"이모지 확인 시간을 **[{args}]**초로 설정 하였습니다.")

	################ 세금 설정 ################ 
	@is_manager()
	@commands.command(name=commandSetting[42][0], aliases=commandSetting[42][1:])
	async def set_tax(self, ctx, *, args : str = None):
		global basicSetting

		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[42][0]} [숫자]** 양식으로 등록 해주세요")
		
		try:
			args = int(args)
		except ValueError:
			return await ctx.send(f"**세율은 [숫자]** 로 입력 해주세요")

		basicSetting[7] = args
		result = self.guild_db.update_one({"_id":"guild"}, {"$set":{"tax":args}}, upsert = True)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 세율 설정 실패.")   

		return  await ctx.send(f"세율을 **[{args}]**%로 설정 하였습니다.")

class adminCog(commands.Cog): 
	def __init__(self, bot):
		self.bot = bot
		
		self.member_db = self.bot.db.jungsan.member
		self.jungsan_db = self.bot.db.jungsan.jungsandata
		self.guild_db = self.bot.db.jungsan.guild
		self.guild_db_log = self.bot.db.jungsan.guild_log
		self.backup_db = self.bot.db.backup.backupdata

	################ 기본설정확인 ################ 
	@commands.command(name=commandSetting[46][0], aliases=commandSetting[46][1:])
	async def setting_info(self, ctx):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		embed = discord.Embed(
			title = f"⚙️ 기본 설정(Server v12)",
			color=0xff00ff
			)
		embed.add_field(name = f"🚫 삭제 주기", value = f"```{basicSetting[4]} 일```")
		embed.add_field(name = f"⌛ 체크 시간", value = f"```{basicSetting[5]} 초```")
		embed.add_field(name = f"⚖️ 수수료", value = f"```{basicSetting[7]} %```")
		embed.add_field(name = f"🗨️ 명령 채널", value = f"```{ctx.message.channel.name}```")
		return await ctx.send(embed = embed, tts=False)

	################ 현재시간 확인 ################ 
	@commands.command(name=commandSetting[37][0], aliases=commandSetting[37][1:])
	async def current_time_check(self, ctx):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return
		now = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		embed = discord.Embed(
			title = f"현재시간은 {now.strftime('%H')}시 {now.strftime('%M')}분 {now.strftime('%S')}초 입니다.",
			color=0xff00ff
			)
		return await ctx.send(embed = embed, tts=False)

	################ 상태메세지 변경 ################ 
	@commands.command(name=commandSetting[38][0], aliases=commandSetting[38][1:])
	async def status_modify(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		if not args:
			return await ctx.send(f"**{commandSetting[38][0]} [내용]** 양식으로 변경 해주세요")

		await self.bot.change_presence(status=discord.Status.dnd, activity=discord.Game(name=args, type=1), afk = False)
		return await ctx.send(f"< 상태메세지 **[ {args} ]**로 변경완료 >", tts=False)

	################ 도움말 ################ 
	@commands.command(name=commandSetting[39][0], aliases=commandSetting[39][1:])
	async def command_help(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return
		
		if args:
			return await ctx.send(f"**{commandSetting[39][0]}만 입력 해주세요!**", tts=False)
		else:
			admin_command_list : str = ""
			admin_command_list += f"{','.join(commandSetting[36])}\n" # 분배채널설정
			admin_command_list += f"{','.join(commandSetting[4])} [아이디]\n"   # 총무등록
			admin_command_list += f"{','.join(commandSetting[5])} [아이디]\n"   # 총무삭제
			
			manager_command_list : str = ""
			manager_command_list += f"{','.join(commandSetting[0])}  ※ 관리자권한도 필요\n"   # 혈원데이터초기화
			manager_command_list += f"{','.join(commandSetting[1])}  ※ 관리자권한도 필요\n"   # 정산데이터초기화
			manager_command_list += f"{','.join(commandSetting[2])}  ※ 관리자권한도 필요\n"   # 혈비데이터초기화
			manager_command_list += f"{','.join(commandSetting[3])}  ※ 관리자권한도 필요\n"   # 백업데이터초기화
			manager_command_list += f"{','.join(commandSetting[40])} [숫자(일)]\n"   # 삭제주기설정
			manager_command_list += f"{','.join(commandSetting[41])} [숫자(초)]\n"   # 확인시간설정
			manager_command_list += f"{','.join(commandSetting[42])} [숫자(%)]\n"   # 세금설정
			manager_command_list += f"{','.join(commandSetting[47])}  ※ 30일 이후 데이터는 삭제됨\n"   # 혈비로그확인
			manager_command_list += f"{','.join(commandSetting[43])} (상세)\n"   # 전체확인
			manager_command_list += f"{','.join(commandSetting[43])} (상세) (검색조건) (검색값)\n"   # 전체확인
			manager_command_list += f"{','.join(commandSetting[55])} [아이디]\n"   # 혈원정보
			manager_command_list += f"{','.join(commandSetting[9])} [아이디] [디스코드ID]\n"   # 혈원입력
			manager_command_list += f"{','.join(commandSetting[54])} [변경아이디] [디스코드ID]\n"   # 혈원변경
			manager_command_list += f"{','.join(commandSetting[10])} [아이디]\n"   # 혈원삭제
			manager_command_list += f"{','.join(commandSetting[30])} [금액] [아이디1] [아이디2]...\n"   # 은행입금
			manager_command_list += f"{','.join(commandSetting[31])} [금액] [아이디1] [아이디2]...\n"   # 은행출금
			manager_command_list += f"{','.join(commandSetting[32])} [금액] (*사유)\n"   # 혈비입금
			manager_command_list += f"{','.join(commandSetting[49])} [금액] *[사유]\n"   # 혈비출금
			manager_command_list += f"{','.join(commandSetting[33])} [금액] [아이디1] [아이디2]... *[사유]\n"   # 혈비지원
			manager_command_list += f"{','.join(commandSetting[53])} [순번] [변경아이디]\n"   # 등록자수정

			member_command_list : str = ""
			member_command_list += f"{','.join(commandSetting[6])}\n"   # 혈원
			member_command_list += f"{','.join(commandSetting[7])} [아이디]\n"   # 혈원등록
			member_command_list += f"{','.join(commandSetting[8])} [아이디]\n\n"   # 혈원수정
			
			member_command_list += f"{','.join(commandSetting[28])}\n"   # 계좌
			member_command_list += f"{','.join(commandSetting[44])} (아이템명)\n"   # 창고
			member_command_list += f"{','.join(commandSetting[11])}\n\n"   # 정산확인
			
			member_command_list += f"{','.join(commandSetting[12])} [보스명] [아이템] [루팅자] [아이디1] [아이디2] ... (참고이미지 url)\n"   # 등록
			member_command_list += f"{','.join(commandSetting[52])} [보스명] [아이템] [루팅자] [뽑을인원] [아이디1] [아이디2] ... (참고이미지 url)\n\n"   # 뽑기등록
			member_command_list += f"----- 등록자만 가능 -----\n"   # 등록자
			member_command_list += f"{','.join(commandSetting[13])} (상세)\n"   # 등록확인1
			member_command_list += f"{','.join(commandSetting[13])} (상세) (검색조건) (검색값)\n"   # 등록확인2
			member_command_list += f"{','.join(commandSetting[14])} [순번] [보스명] [아이템] [루팅자] [아이디1] [아이디2] ...\n"   # 등록수정
			member_command_list += f"{','.join(commandSetting[15])} [순번]\n\n"   # 등록삭제
			member_command_list += f"----- 루팅자만 가능 -----\n"   # 루팅자
			member_command_list += f"{','.join(commandSetting[16])} (상세)\n"   # 루팅확인1
			member_command_list += f"{','.join(commandSetting[16])} (상세) (검색조건) (검색값)\n"   # 루팅확인2
			member_command_list += f"{','.join(commandSetting[17])} [순번] [보스명] [아이템] [루팅자] [아이디1] [아이디2] ...\n"   # 루팅수정
			member_command_list += f"{','.join(commandSetting[18])} [순번]\n\n"   # 루팅삭제
			member_command_list += f"----- 등록자, 루팅자만 가능 -----\n"   # 등록자, 루팅자
			member_command_list += f"{','.join(commandSetting[19])} [순번] [변경보스명]\n"   # 보스수정
			member_command_list += f"{','.join(commandSetting[20])} [순번] [변경아이템명]\n"   # 템수정
			member_command_list += f"{','.join(commandSetting[21])} [순번] [변경아이디]\n"   # 토글수정
			member_command_list += f"{','.join(commandSetting[22])} [순번] [추가아이디]\n"   # 참여자추가
			member_command_list += f"{','.join(commandSetting[23])} [순번] [삭제아이디]\n"   # 참여자삭제
			member_command_list += f"{','.join(commandSetting[50])} [순번] [수정이미지 url]\n"   # 이미지수정
			member_command_list += f"{','.join(commandSetting[24])} [순번] [금액]\n"   # 판매
			member_command_list += f"{','.join(commandSetting[45])} [순번] [금액] [뽑을인원]\n"   # 뽑기판매
			member_command_list += f"{','.join(commandSetting[51])} [순번]\n"   # 판매취소
			member_command_list += f"{','.join(commandSetting[29])} [순번] [금액]\n"   # 저축
			member_command_list += f"{','.join(commandSetting[48])} [순번] [금액] [뽑을인원]\n"   # 뽑기저축
			member_command_list += f"{','.join(commandSetting[25])} [순번] [아이디]\n"   # 정산
			member_command_list += f"{','.join(commandSetting[26])} [순번] [아이디]\n"   # 정산취소
			member_command_list += f"{','.join(commandSetting[27])}\n"   # 일괄정산1
			member_command_list += f"{','.join(commandSetting[27])} (검색조건) (검색값)\n"   # 일괄정산2

			etc_command_list : str = ""
			etc_command_list += f"{','.join(commandSetting[46])}\n"   # 기본설정확인
			etc_command_list += f"{','.join(commandSetting[37])}\n"   # 현재시간
			etc_command_list += f"{','.join(commandSetting[38])} [변경메세지]\n"   # 상태
			etc_command_list += f"{','.join(commandSetting[34])} [금액] (거래소세금)\n"   # 수수료
			etc_command_list += f"{','.join(commandSetting[35])} [거래소금액] [실거래가] (거래소세금)\n"   # 페이백
			
			embed = discord.Embed(
					title = "🕹️ 분배봇 사용법",
					description= f"```득템 → 정산등록 → 판매입력 → 정산처리 → 끝!```",
					color=0xff00ff
					)
			embed.add_field(name = f"⚙️ [ 관리자 전용 명령어 ]", value = f"```css\n{admin_command_list}```", inline = False)
			embed.add_field(name = f"🤴 [ 총무 전용 명령어 ]", value = f"```css\n{manager_command_list}```", inline = False)
			embed.add_field(name = f"🧑 [ 일반 명령어 ]", value = f"```css\n{member_command_list}```", inline = False)
			embed.add_field(name = f"🔧 [ 기타 명령어 ]", value = f"```css\n{etc_command_list}```", inline = False)
			embed.set_footer(text = f"※ '분배완료'된 것 중 30일이 지난 건은 자동으로 삭제\n    '미입력' 상태의 등록건만 수정 가능\n    '분배중' 상태의 등록건만 정산 가능\n    거래소세금 : 미입력시 {basicSetting[7]}%\n    등록시 참고이미지url은 [ https:// ]로 시작해야함")
			return await ctx.send( embed=embed, tts=False)

	################ member_db초기화 ################ .
	@is_manager()
	@commands.has_permissions(manage_guild=True)
	@commands.command(name=commandSetting[0][0], aliases=commandSetting[0][1:])
	async def initialize_all_member_data(self, ctx):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		emoji_list : list = ["⭕", "❌"]

		delete_warning_message = await ctx.send(f"**혈원데이터를 초기화 하시면 다시는 복구할 수 없습니다. 정말로 초기화하시겠습니까?**\n**초기화 : ⭕ 취소: ❌**\n({int(basicSetting[5])*2}초 동안 입력이 없을시 초기화가 취소됩니다.)", tts=False)
		
		for emoji in emoji_list:
			await delete_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == delete_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5])*2)
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await delete_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **초기화**를 취소합니다!")

		if str(reaction) == "⭕":
			self.member_db.delete_many({})
			print(f"< 혈원데이터 초기화 완료 >")
			return await ctx.send(f"☠️ 혈원데이터 초기화 완료! ☠️")
		else:
			return await ctx.send(f"**초기화**가 취소되었습니다.\n")		

	################ jungsan_db초기화 ################
	@is_manager()
	@commands.has_permissions(manage_guild=True)
	@commands.command(name=commandSetting[1][0], aliases=commandSetting[1][1:])
	async def initialize_all_jungsan_data(self, ctx):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		emoji_list : list = ["⭕", "❌"]

		delete_warning_message = await ctx.send(f"**정산데이터를 초기화 하시면 다시는 복구할 수 없습니다. 정말로 초기화하시겠습니까?**\n**초기화 : ⭕ 취소: ❌**\n({int(basicSetting[5])*2}초 동안 입력이 없을시 초기화가 취소됩니다.)", tts=False)
		
		for emoji in emoji_list:
			await delete_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == delete_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5])*2)
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await delete_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **초기화**를 취소합니다!")

		if str(reaction) == "⭕":
			self.jungsan_db.delete_many({})
			print(f"< 정산데이터 초기화 완료 >")
			return await ctx.send(f"☠️ 정산데이터 초기화 완료! ☠️")
		else:
			return await ctx.send(f"**초기화**가 취소되었습니다.\n")		

	################ guild_db초기화 ################
	@is_manager()
	@commands.has_permissions(manage_guild=True)
	@commands.command(name=commandSetting[2][0], aliases=commandSetting[2][1:])
	async def initialize_all_guild_data(self, ctx):
		global basicSetting
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		emoji_list : list = ["⭕", "❌"]

		delete_warning_message = await ctx.send(f"**혈비데이터를 초기화 하시면 다시는 복구할 수 없습니다. 정말로 초기화하시겠습니까?**\n**초기화 : ⭕ 취소: ❌**\n({int(basicSetting[5])*2}초 동안 입력이 없을시 초기화가 취소됩니다.)", tts=False)
		
		for emoji in emoji_list:
			await delete_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == delete_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5])*2)
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await delete_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **초기화**를 취소합니다!")

		if str(reaction) == "⭕":
			self.guild_db.delete_many({})
			self.guild_db_log.delete_many({})
			init_guild_data : dict = {
				"guild_money":0,
				"back_up_period":14,
				"checktime":15,
				"distributionchannel":0,
				"tax":5
				}
			update_guild_data : dict = self.guild_db.update_one({"_id":"guild"}, {"$set":init_guild_data}, upsert = True)

			basicSetting[4] = init_guild_data['back_up_period']
			basicSetting[5] = init_guild_data['checktime']
			basicSetting[6] = init_guild_data['distributionchannel']
			basicSetting[7] = init_guild_data['tax']
			
			# basicSetting[4] = backup_period
			# basicSetting[5] = checktime
			# basicSetting[6] = distributionchannel
			# basicSetting[7] = tax

			print(f"< 혈비/로그 데이터 초기화 완료 >")
			return await ctx.send(f"☠️ 혈비/로그 데이터 초기화 완료! ☠️\n**[{commandSetting[36][0]}]** 명령어를 입력하신 후 사용해주시기 바랍니다.")
		else:
			return await ctx.send(f"**초기화**가 취소되었습니다.\n")	

	################ backup_db초기화 ################
	@is_manager()
	@commands.has_permissions(manage_guild=True)
	@commands.command(name=commandSetting[3][0], aliases=commandSetting[3][1:])
	async def initialize_all_backup_data(self, ctx):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		emoji_list : list = ["⭕", "❌"]

		delete_warning_message = await ctx.send(f"**백업데이터를 초기화 하시면 다시는 복구할 수 없습니다. 정말로 초기화하시겠습니까?**\n**초기화 : ⭕ 취소: ❌**\n({int(basicSetting[5])*2}초 동안 입력이 없을시 초기화가 취소됩니다.)", tts=False)
		
		for emoji in emoji_list:
			await delete_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == delete_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5])*2)
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await delete_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **초기화**를 취소합니다!")

		if str(reaction) == "⭕":
			self.backup_db.delete_many({})
			print(f"< 백업데이터 초기화 완료 >")
			return await ctx.send(f"☠️ 백업데이터 초기화 완료! ☠️")
		else:
			return await ctx.send(f"**초기화**가 취소되었습니다.\n")

	################ 혈비로그확인 ################ 
	@is_manager()
	@commands.command(name=commandSetting[47][0], aliases=commandSetting[47][1:])
	async def guild_log_load(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if args:
			return await ctx.send(f"**{commandSetting[47][0]}** 양식으로 등록 해주세요")

		result : list = []

		result = list(self.guild_db_log.find({}))

		if len(result) == 0:
			return await ctx.send(f"```혈비 로그가 없습니다!```")

		sorted_result = sorted(list([result_data['log_date'] for result_data in result]))

		log_date_list : list = []
		log_date_list = sorted(list(set([result_data['log_date'].strftime('%y-%m-%d') for result_data in result])))
		
		total_distribute_money : int = 0
		embed_list : list = []
		embed_limit_checker : int = 0
		embed_cnt : int = 0
		detail_title_info	: str = ""
		detail_info	: str = ""
		
		embed = discord.Embed(
					title = f"📜 혈비 로그",
					description = "",
					color=0x00ff00
					)
		embed_list.append(embed)
		for date in log_date_list:
			embed_limit_checker = 0
			detail_info	: str = ""
			for result_data1 in result:
				if embed_limit_checker == 50:
					embed_limit_checker = 0
					embed_cnt += 1
					tmp_embed = discord.Embed(
						title = "",
						description = "",
						color=0x00ff00
						)
					embed_list.append(tmp_embed)
				if result_data1['log_date'].strftime('%y-%m-%d') == date:
					embed_limit_checker += 1
					if result_data1['in_out_check']:
						if result_data1['reason'] != "":
							if not result_data1['member_list']:
								detail_info += f"+ 💰 {result_data1['money']} : {result_data1['reason']}\n"
							else:
								detail_info += f"+ 💰 {result_data1['money']} : {', '.join(result_data1['member_list'])} (사유 : {result_data1['reason']})\n"
						else:
							detail_info += f"+ 💰 {result_data1['money']} : 혈비 입금\n"
					else:
						if result_data1['reason'] != "":
							detail_info += f"- 💰 {result_data1['money']} : {', '.join(result_data1['member_list'])} (사유:{result_data1['reason']})\n"
						else:
							detail_info += f"- 💰 {result_data1['money']} : {', '.join(result_data1['member_list'])}\n"
				
				embed_list[embed_cnt].title = f"🗓️ {date}"
				embed_list[embed_cnt].description = f"```diff\n{detail_info}```"

			if len(embed_list) > 1:
				for embed_data in embed_list:
					await asyncio.sleep(0.1)
					await ctx.send(embed = embed_data)
			else:
				await asyncio.sleep(0.1)
				await ctx.send(embed = embed)
		return

class memberCog(commands.Cog): 
	def __init__(self, bot):
		self.bot = bot	

		self.member_db = self.bot.db.jungsan.member
		self.jungsan_db = self.bot.db.jungsan.jungsandata
		self.guild_db = self.bot.db.jungsan.guild
		self.guild_db_log = self.bot.db.jungsan.guild_log

	################ 총무등록 ################ 
	@commands.has_permissions(manage_guild=True)
	@commands.command(name=commandSetting[4][0], aliases=commandSetting[4][1:])
	async def set_manager(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"game_ID":args})

		if not member_data:
			return await ctx.send(f"**[{args}]**님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[4][0]} [아이디]** 양식으로 등록 해주세요")

		result = self.member_db.update_one({"game_ID":member_data["game_ID"]}, {"$set":{"permissions":"manager"}}, upsert = True)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 총무 등록 실패.")   

		return  await ctx.send(f"**[{args}]**님을 총무로 등록 하였습니다.")

	################ 총무삭제 ################ 
	@commands.has_permissions(manage_guild=True)
	@commands.command(name=commandSetting[5][0], aliases=commandSetting[5][1:])
	async def delete_manager(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"game_ID":args})

		if not member_data:
			return await ctx.send(f"**[{args}]**님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[5][0]} [아이디]** 양식으로 삭제 해주세요")

		result = self.member_db.update_one({"game_ID":member_data["game_ID"]}, {"$set":{"permissions":"member"}}, upsert = True)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 총무 삭제 실패.")   

		return  await ctx.send(f"**[{args}]**님을 총무에서 삭제 하였습니다.")

	################ 혈원목록 확인 ################ 
	@commands.command(name=commandSetting[6][0], aliases=commandSetting[6][1:])
	async def member_list(self, ctx):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		remain_guild_money : int = 0

		guild_data : dict = self.guild_db.find_one({"_id":"guild"})

		if not guild_data:
			remain_guild_money = 0
		else:
			remain_guild_money = guild_data["guild_money"]
			
		member_list : str = ""
		manager_list : str = ""

		member_document : list = list(self.member_db.find({}))

		sorted_member_document : dict = sorted(member_document, key=lambda member_document:member_document['account'], reverse = True)

		total_account : int = sum(member['account'] for member in sorted_member_document)

		for member_info in sorted_member_document:
			if member_info["permissions"] == "manager":
				if member_info['account'] != 0:
					manager_list += f"{member_info['game_ID']}({member_info['account']}) "
				else:
					manager_list += f"{member_info['game_ID']} "
			else:
				if member_info['account'] != 0:
					member_list += f"{member_info['game_ID']}({member_info['account']}) "
				else:
					member_list += f"{member_info['game_ID']} "

		embed = discord.Embed(
		title = "👥  혈원 목록",
		description = "",
		color=0x00ff00
		)
		if len(manager_list) == 0:
			embed.add_field(name = f"**🤴 총무**",value = f"**```cs\n등록된 총무가 없습니다.```**")
		else:
			embed.add_field(name = f"**🤴 총무**",value = f"**```cs\n{manager_list}```**")
		if len(member_list) == 0:
			embed.add_field(name = f"**🧑 혈원**",value = f"**```cs\n등록된 혈원이 없습니다.```**", inline = False)
		else:
			embed.add_field(name = f"**🧑 혈원**",value = f"**```cs\n{member_list}```**", inline = False)
		embed.add_field(name = f"**👤 혈원수**",value = f"**```fix\n{len(sorted_member_document)}```**")
		embed.add_field(name = f"**🏦 잔고**",value = f"**```fix\n{total_account}```**")
		embed.add_field(name = f"**💰 혈비**",value = f"**```fix\n{remain_guild_money}```**")
		#embed.set_footer(text = f"👑 표시는 총무!")
		return await ctx.send(embed = embed)

	################ 혈원아이디 등록 ################ 
	@commands.command(name=commandSetting[7][0], aliases=commandSetting[7][1:])
	async def member_add(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		if not args:
			return await ctx.send(f"**{commandSetting[7][0]} [아이디]** 양식으로 추가 해주세요")

		member_document : dict = self.member_db.find_one({ "_id":ctx.author.id})
		member_game_ID_document : dict = self.member_db.find_one({ "game_ID":args})

		if member_document:
			return await ctx.send(f"```이미 등록되어 있습니다!```")

		if member_game_ID_document:
			return await ctx.send(f"```이미 등록된 [아이디]입니다!```")

		result = self.member_db.update_one({"_id":ctx.author.id}, {"$set":{"game_ID":args, "discord_name":self.bot.get_user(ctx.author.id).display_name, "permissions":"member", "account":0}}, upsert = True)

		# "_id" : int = discord_ID
		# "game_ID" : str = game_ID
		# "discord_name" : str = discord_nickname
		# "permissiotns" : str = 권한 ["manager", "member"]
		# "account" : int = 은행잔고

		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 혈원 등록 실패.")   

		return await ctx.send(f"{ctx.author.mention}님! **[{args}] [{ctx.author.id}]**(으)로 혈원 등록 완료!")

	################ 혈원아이디 수정 ################ 
	@commands.command(name=commandSetting[8][0], aliases=commandSetting[8][1:])
	async def member_modify(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({ "_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[8][0]} [아이디]** 양식으로 수정 해주세요")

		member_game_ID_document : dict = self.member_db.find_one({ "game_ID":args})

		if member_game_ID_document:
			return await ctx.send(f"```이미 등록된 [ 아이디 ] 입니다!```")

		jungsan_document = list(self.jungsan_db.find({"$and" : [{"$or" : [{"before_jungsan_ID" : member_data['game_ID']}, {"after_jungsan_ID" : member_data['game_ID']}, {"toggle" : member_data['game_ID']}, {"regist" : member_data['game_ID']}]}, {"$or" : [{"itemstatus" : "분배중"}, {"itemstatus" : "미판매"}]}]}))
		len_jungsan_document : int = len(jungsan_document)
		tmp_before_data : list = []
		tmp_after_data : list = []
		tmp_toggle_data : str = ""
		tmp_regist_data : str = ""
		
		if len_jungsan_document != 0:
			for jungsan_data in jungsan_document:
				tmp_before_data = jungsan_data["before_jungsan_ID"]
				tmp_after_data = jungsan_data["after_jungsan_ID"]
				tmp_toggle_data = jungsan_data["toggle"]
				tmp_regist_data = jungsan_data["regist"]
				
				if member_data['game_ID'] in jungsan_data["before_jungsan_ID"]:
					jungsan_data["before_jungsan_ID"].remove(member_data['game_ID'])
					jungsan_data["before_jungsan_ID"].append(args)
					tmp_before_data = jungsan_data["before_jungsan_ID"]
					#result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":{"before_jungsan_ID":jungsan_data["before_jungsan_ID"]}}, upsert = False)
				
				if member_data['game_ID'] in jungsan_data["after_jungsan_ID"]:
					jungsan_data["after_jungsan_ID"].remove(member_data['game_ID'])
					jungsan_data["after_jungsan_ID"].append(args)
					tmp_after_data = jungsan_data["after_jungsan_ID"]
					#result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":{"after_jungsan_ID":jungsan_data["after_jungsan_ID"]}}, upsert = False)
				
				if member_data['game_ID'] in jungsan_data["toggle"]:
					tmp_toggle_data = args
					#result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":{"toggle":args}}, upsert = False)

				if member_data['game_ID'] in jungsan_data["regist"]:
					tmp_regist_data = args
				
				result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":{"regist":tmp_regist_data, "toggle":tmp_toggle_data,"before_jungsan_ID":sorted(tmp_before_data) , "after_jungsan_ID":sorted(tmp_after_data)}}, upsert = False)

		result = self.member_db.update_one({"_id":ctx.author.id}, {"$set":{"game_ID":args}}, upsert = True)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 아이디 수정 실패.")   

		return await ctx.send(f"{ctx.author.mention}님, 아이디를 **[{member_data['game_ID']}]**에서 **[{args}]**로 변경하였습니다.")

	################ 혈원아이디 정보 ################ 
	@commands.command(name=commandSetting[55][0], aliases=commandSetting[55][1:])
	async def member_infomation(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		if not args:
			return await ctx.send(f"**{commandSetting[55][0]} [아이디]** 양식으로 입력 해주세요")

		member_data : dict = self.member_db.find_one({"game_ID":args})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		embed = discord.Embed(
			title = f"👤 **[{member_data['game_ID']}]님의 정보**",
			color=0x00ff00
			)
		embed.add_field(name = "디스코드 🆔", value = f"```fix\n{member_data['_id']}```", inline=False)
		if member_data['permissions'] == "manager":
			embed.add_field(name = "💪 권한", value = f"```fix\n총무```")
		else:
			embed.add_field(name = "💪 권한", value = f"```fix\n혈원```")
		embed.add_field(name = "🏦 잔고", value = f"```fix\n{member_data['account']}```")

		return await ctx.send(embed=embed)

	################ 혈원아이디 입력 ################ 
	@is_manager()
	@commands.command(name=commandSetting[9][0], aliases=commandSetting[9][1:])
	async def member_input_add(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		if not args:
			return await ctx.send(f"**{commandSetting[9][0]} [아이디] [디코ID]** 양식으로 추가 해주세요")

		input_regist_data : list = args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data < 2:
			return await ctx.send(f"**{commandSetting[9][0]} [아이디] [디코ID]** 양식으로 추가 해주세요")

		member_document : dict = self.member_db.find_one({"_id":int(input_regist_data[1])})
		member_game_ID_document : dict = self.member_db.find_one({"game_ID":input_regist_data[0]})

		if member_document:
			return await ctx.send(f"```이미 등록되어 있습니다!```")

		if member_game_ID_document:
			return await ctx.send(f"```이미 등록된 [ 아이디 ] 입니다!```")

		result = self.member_db.update_one({"_id":int(input_regist_data[1])}, {"$set":{"game_ID":input_regist_data[0], "discord_name":self.bot.get_user(int(input_regist_data[1])).display_name, "permissions":"member", "account":0}}, upsert = True)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"**[{input_regist_data[0]}] [{input_regist_data[1]}]**(으)로 혈원 등록 실패.")   

		return await ctx.send(f"**[{input_regist_data[0]}] [{input_regist_data[1]}]**(으)로 혈원 등록 완료!")

	################ 혈원아이디 변경 ################ 
	@commands.command(name=commandSetting[54][0], aliases=commandSetting[54][1:])
	async def member_forced_modify(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		if not args:
			return await ctx.send(f"**{commandSetting[54][0]} [아이디] [디코ID]** 양식으로 변경 해주세요")

		input_regist_data : list = args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data < 2:
			return await ctx.send(f"**{commandSetting[54][0]} [아이디] [디코ID]** 양식으로 변경 해주세요")

		member_data : dict = self.member_db.find_one({"_id":int(input_regist_data[1])})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님, 해당 아이디를 가진 혈원은 등록되어 있지 않습니다!")

		if member_data["game_ID"] == input_regist_data[0]:
			return await ctx.send(f"{ctx.author.mention}님, 기존 아이디와 변경 아이디가 동일합니다!")

		member_game_ID_document : dict = self.member_db.find_one({"game_ID":input_regist_data[0]})

		if member_game_ID_document:
			return await ctx.send(f"```이미 등록된 [ 아이디 ] 입니다!```")

		jungsan_document = list(self.jungsan_db.find({"$and" : [{"$or" : [{"before_jungsan_ID" : member_data['game_ID']}, {"after_jungsan_ID" : member_data['game_ID']}, {"toggle" : member_data['game_ID']}, {"regist" : member_data['game_ID']}]}, {"$or" : [{"itemstatus" : "분배중"}, {"itemstatus" : "미판매"}]}]}))
		len_jungsan_document : int = len(jungsan_document)
		tmp_before_data : list = []
		tmp_after_data : list = []
		tmp_toggle_data : str = ""
		tmp_regist_data : str = ""
		
		if len_jungsan_document != 0:
			for jungsan_data in jungsan_document:
				tmp_before_data = jungsan_data["before_jungsan_ID"]
				tmp_after_data = jungsan_data["after_jungsan_ID"]
				tmp_toggle_data = jungsan_data["toggle"]
				tmp_regist_data = jungsan_data["regist"]
				
				if member_data['game_ID'] in jungsan_data["before_jungsan_ID"]:
					jungsan_data["before_jungsan_ID"].remove(member_data['game_ID'])
					jungsan_data["before_jungsan_ID"].append(input_regist_data[0])
					tmp_before_data = jungsan_data["before_jungsan_ID"]
				
				if member_data['game_ID'] in jungsan_data["after_jungsan_ID"]:
					jungsan_data["after_jungsan_ID"].remove(member_data['game_ID'])
					jungsan_data["after_jungsan_ID"].append(input_regist_data[0])
					tmp_after_data = jungsan_data["after_jungsan_ID"]
				
				if member_data['game_ID'] in jungsan_data["toggle"]:
					tmp_toggle_data = input_regist_data[0]

				if member_data['game_ID'] in jungsan_data["regist"]:
					tmp_regist_data = input_regist_data[0]
				
				result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":{"regist":tmp_regist_data, "toggle":tmp_toggle_data,"before_jungsan_ID":sorted(tmp_before_data) , "after_jungsan_ID":sorted(tmp_after_data)}}, upsert = False)

		result = self.member_db.update_one({"_id":int(input_regist_data[1])}, {"$set":{"game_ID":input_regist_data[0]}}, upsert = True)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, {member_data['game_ID']}님 아이디 변경 실패.")   

		return await ctx.send(f"{ctx.author.mention}님, **{member_data['game_ID']}**님 아이디를 **[{input_regist_data[0]}]**로 변경하였습니다.")

	################ 혈원아이디 삭제 ################ 
	@is_manager()
	@commands.command(name=commandSetting[10][0], aliases=commandSetting[10][1:])
	async def member_delete(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return
			
		member_data : dict = self.member_db.find_one({"game_ID":args})

		if not member_data:
			return await ctx.send(f"**[{args}]**님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[10][0]} [아이디]** 양식으로 삭제 해주세요")

		jungsan_document = list(self.jungsan_db.find({"$and" : [{"$or": [{"before_jungsan_ID" : args}, {"toggle" : args}, {"regist" : args}]}, {"$or": [{"itemstatus" : "분배중"}, {"itemstatus" : "미판매"}]}]}))
		len_jungsan_document : int = len(jungsan_document)
		
		if len_jungsan_document != 0:
			remain_jungsan_info : str = ""
			plus_remain_money : int = 0
			minus_remain_money : int = 0
			total_remain_money : int = 0
			for jungsan_data in jungsan_document:
				tmp_str : str = f"[순번:{jungsan_data['_id']}]({jungsan_data['itemstatus']}) "
				if jungsan_data["regist"] == args:
					tmp_str += f"[등록] "
				if jungsan_data["toggle"] == args:
					tmp_str += f"[루팅] "
					if jungsan_data['price'] != 0:
						minus_remain_money += jungsan_data['price']
						tmp_str += f"<-{jungsan_data['price']}> "
				if args in jungsan_data["before_jungsan_ID"]:
					if jungsan_data["itemstatus"] == "분배중":
						plus_remain_money += jungsan_data["each_price"]
						tmp_str += f"[참여]|{jungsan_data['price']}/{len(jungsan_data['before_jungsan_ID'])}| < +{jungsan_data['each_price']} >"
					else:
						tmp_str += f"[참여]"

				remain_jungsan_info += f"{tmp_str}\n"
						
			total_remain_money = plus_remain_money - minus_remain_money

			await ctx.send(f"```잔여 등록/루팅/정산 목록이 있어 혈원을 삭제할 수 없습니다.```")
			embed = discord.Embed(
				title = "📜 잔여 등록/루팅/정산 목록",
				description = f"```md\n{remain_jungsan_info}```",
				color=0x00ff00
				)
			embed.add_field(name = "\u200b", value = f"은행 잔고 : 💰 **{member_data['account']}**\n정산 금액 : 💰 **{total_remain_money}**")
			embed.add_field(name = "\u200b", value = f"잔여 목록을 `일괄정산`하고 혈원[`{args}`]을(를) `삭제` 하고 싶으면 `{int(basicSetting[5])*2}초`내로 ✅를 `클릭`해 주세요!", inline = False)
			embed.set_footer(text = f"일괄정산 처리를 원하지 않는 경우 등록내역 수정 등을 통해 혈원[{args}]에 대한 정보를 삭제 후 다시 삭제요청 바랍니다.")
			remain_jungsan_info_msg = await ctx.send(embed = embed)

			emoji_list : list = ["✅", "❌"]

			for emoji in emoji_list:
				await remain_jungsan_info_msg.add_reaction(emoji)

			def reaction_check(reaction, user):
				return (reaction.message.id == remain_jungsan_info_msg.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

			try:
				reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5])*2)
			except asyncio.TimeoutError:
				for emoji in emoji_list:
					await remain_jungsan_info_msg.remove_reaction(emoji, self.bot.user)
				return await ctx.send(f"시간이 초과됐습니다. **혈원삭제**를 취소합니다!")

			if str(reaction) == "✅":
				for jungsan_data in jungsan_document:
					result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":{"before_jungsan_ID":[], "after_jungsan_ID":sorted(jungsan_data['after_jungsan_ID']+jungsan_data['before_jungsan_ID']), "modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])), "itemstatus":"분배완료"}}, upsert = True)
					if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
						await ctx.send(f"{ctx.author.mention}, 일괄정산 실패.") 
				await ctx.send(f"📥 일괄정산 완료! 📥")
			else:
				return await ctx.send(f"**혈원삭제**를 취소하였습니다!")

		result = self.member_db.delete_one({"game_ID":args})
		
		return  await ctx.send(f"**[{args}]**님을 혈원에서 삭제 하였습니다.")

class manageCog(commands.Cog): 
	def __init__(self, bot):
		self.bot = bot
		self.index_value = 0
				
		self.member_db = self.bot.db.jungsan.member
		self.jungsan_db = self.bot.db.jungsan.jungsandata
		self.guild_db = self.bot.db.jungsan.guild
		self.guild_db_log = self.bot.db.jungsan.guild_log

		try:
			self.db_index = self.jungsan_db.find().sort([("_id",-1)]).limit(1)
			self.index_value = list(self.db_index)[0]["_id"]
		except:
			pass

	################ 참여자 ################ 
	################ 참여내역 및 정산금 확인 ################ 
	@commands.command(name=commandSetting[11][0], aliases=commandSetting[11][1:])
	async def participant_data_check(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		jungsan_document : list = []
		if not args:
			jungsan_document = list(self.jungsan_db.find({"$and" : [{"before_jungsan_ID" : member_data['game_ID']}, {"$or" : [{"itemstatus" : "분배중"}, {"itemstatus" : "미판매"}]}]}))
		else:
			input_distribute_all_finish : list = args.split()
			len_input_distribute_all_finish = len(input_distribute_all_finish)

			if len_input_distribute_all_finish != 2:
				return await ctx.send(f"**{commandSetting[11][0]} [검색조건] [검색값]** 형식으로 입력 해주세요! **[검색조건]**은 **[순번, 보스명, 아이템, 날짜, 분배상태]** 다섯가지 중 **1개**를 입력 하셔야합니다!")
			else:
				if input_distribute_all_finish[0] == "순번":
					try:
						input_distribute_all_finish[1] = int(input_distribute_all_finish[1])
					except:
						return await ctx.send(f"**[순번] [검색값]**은 \"숫자\"로 입력 해주세요!")
					jungsan_document : dict = self.jungsan_db.find_one({"$and" : [{"before_jungsan_ID" : member_data['game_ID']}, {"_id":input_distribute_all_finish[1]}, {"$or" : [{"itemstatus" : "분배중"}, {"itemstatus" : "미판매"}]}]})
					if not jungsan_document:
						return await ctx.send(f"{ctx.author.mention}님! 수령할 정산 내역이 없습니다.")
					embed = get_detail_embed(jungsan_document)
					try:
						return await ctx.send(embed = embed)
					except Exception:
						embed.add_field(name = "🚫  이미지 링크 확인 필요  🚫", value = f"```저장된 이미지가 삭제됐습니다.```")
						embed.set_image(url = "")
						result1 = self.jungsan_db.update_one({"_id":input_distribute_all_finish[1]}, {"$set":{"image_url":""}}, upsert = True)
						if result1.raw_result["nModified"] < 1 and "upserted" not in result1.raw_result:
							return await ctx.send(f"{ctx.author.mention}, 정산 등록 실패.") 
						return await ctx.send(embed = embed)
				elif input_distribute_all_finish[0] == "보스명":
					jungsan_document = list(self.jungsan_db.find({"$and" : [{"before_jungsan_ID" : member_data['game_ID']}, {"boss":input_distribute_all_finish[1]}, {"$or" : [{"itemstatus" : "분배중"}, {"itemstatus" : "미판매"}]}]}))
				elif input_distribute_all_finish[0] == "아이템":
					jungsan_document = list(self.jungsan_db.find({"$and" : [{"before_jungsan_ID" : member_data['game_ID']}, {"item":input_distribute_all_finish[1]}, {"$or" : [{"itemstatus" : "분배중"}, {"itemstatus" : "미판매"}]}]}))
				elif input_distribute_all_finish[0] == "날짜":
					try:
						start_search_date : str = (datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))).replace(year = int(input_distribute_all_finish[1][:4]), month = int(input_distribute_all_finish[1][5:7]), day = int(input_distribute_all_finish[1][8:10]), hour = 0, minute = 0, second = 0)
						end_search_date : str = start_search_date + datetime.timedelta(days = 1)
					except:
						return await ctx.send(f"**[날짜] [검색값]**은 0000-00-00 형식으로 입력 해주세요!")
					jungsan_document = list(self.jungsan_db.find({"$and" : [{"before_jungsan_ID" : member_data['game_ID']}, {"getdate":{"$gte":start_search_date, "$lt":end_search_date}}, {"$or" : [{"itemstatus" : "분배중"}, {"itemstatus" : "미판매"}]}]}))
				elif input_distribute_all_finish[0] == "분배상태":
					if input_distribute_all_finish[1] == "분배중":
						jungsan_document = list(self.jungsan_db.find({"$and" : [{"before_jungsan_ID" : member_data['game_ID']}, {"itemstatus" : "분배중"}]}))
					elif input_distribute_all_finish[1] == "미판매":
						jungsan_document = list(self.jungsan_db.find({"$and" : [{"before_jungsan_ID" : member_data['game_ID']}, {"itemstatus" : "미판매"}]}))
					else:
						return await ctx.send(f"**[분배상태] [검색값]**은 \"미판매\" 혹은 \"분배중\"로 입력 해주세요!")
				else:
					return await ctx.send(f"**[검색조건]**이 잘못 됐습니다. **[검색조건]**은 **[순번, 보스명, 아이템, 날짜, 분배상태]** 다섯가지 중 **1개**를 입력 하셔야합니다!")

		if len(jungsan_document) == 0:
			return await ctx.send(f"{ctx.author.mention}님! 수령할 정산 내역이 없습니다.")

		total_money : int = 0
		toggle_list : list = []
		toggle_list = sorted(list(set([jungsan_data['toggle'] for jungsan_data in jungsan_document])))

		if "혈비" in toggle_list:
			toggle_list.remove("혈비")

		embed = discord.Embed(
				title = f"📜 [{member_data['game_ID']}]님 정산 내역",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = f"🏦 **[ 은행 ]**", value = f"**```fix\n {member_data['account']}```**")
		for game_id in toggle_list:
			each_price : int = 0
			info_cnt : int = 0
			tmp_info : list = []
			tmp_info.append("")
			for jungsan_data in jungsan_document:
				if jungsan_data['toggle'] == game_id:
					if len(tmp_info[info_cnt]) > 900:
						tmp_info.append("")
						info_cnt += 1
					if jungsan_data['itemstatus'] == "미판매":
						tmp_info[info_cnt] += f"-[순번:{jungsan_data['_id']}]|{jungsan_data['getdate'].strftime('%y-%m-%d')}|{jungsan_data['boss']}|{jungsan_data['item']}|{jungsan_data['itemstatus']}\n"
					else:
						each_price += jungsan_data['each_price']
						if jungsan_data["ladder_check"]:
							tmp_info[info_cnt] += f"+[순번:{jungsan_data['_id']}]|{jungsan_data['getdate'].strftime('%y-%m-%d')}|{jungsan_data['boss']}|{jungsan_data['item']}|🌟|💰{jungsan_data['each_price']}\n"
						else:
							tmp_info[info_cnt] += f"+[순번:{jungsan_data['_id']}]|{jungsan_data['getdate'].strftime('%y-%m-%d')}|{jungsan_data['boss']}|{jungsan_data['item']}|💰{jungsan_data['each_price']}\n"
			total_money += each_price
			if len(tmp_info) > 1:
				embed.add_field(
					name = f"[ {game_id} ]님께 받을 내역 (총 💰 {each_price} )",
					value = f"```diff\n{tmp_info[0]}```",
					inline = False
					)
				for i in range(len(tmp_info)-1):
					embed.add_field(
						name = f"\u200b",
						value = f"```diff\n{tmp_info[i+1]}```",
						inline = False
						)
			else:
				embed.add_field(
						name = f"[ {game_id} ]님께 받을 내역 (총 💰 {each_price} )",
						value = f"```diff\n{tmp_info[0]}```",
						inline = False
						)
		await ctx.send(embed = embed)
		if int(total_money) == 0:
			return
		else:
			embed1 = discord.Embed(
				title = f"총 수령 예정 금액 : 💰 {total_money}",
				description = "",
				color=0x00ff00
				)
			return await ctx.send(embed = embed1)

	################ 등록자 ################ 
	################ 분배등록 ################ 
	@commands.command(name=commandSetting[12][0], aliases=commandSetting[12][1:])
	async def regist_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[12][0]} [보스명] [아이템명] [루팅자] [참여자1] [참여자2]...** 양식으로 등록 해주세요")

		tmp_args : str = ""
		tmp_image_url : str = ""

		if args.find("https://") != -1:
			tmp_data = args.split("https://")
			tmp_args = tmp_data[0]
			tmp_image_url = f"https://{tmp_data[1]}"
		else:
			tmp_args = args
		
		input_regist_data : list = tmp_args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data < 4:
			return await ctx.send(f"**{commandSetting[12][0]} [보스명] [아이템명] [루팅자] [참여자1] [참여자2]...** 양식으로 등록 해주세요")

		check_member_data : list = []
		check_member_list : list = []
		wrong_input_id : list = []
		gulid_money_insert_check : bool = False
		loot_member_data : dict = {}

		if input_regist_data[2] == "혈비":
			gulid_money_insert_check = True
			loot_member_data = {"_id":ctx.author.id}
		else:
			gulid_money_insert_check = False
			loot_member_data = self.member_db.find_one({"game_ID":input_regist_data[2]})
			if not loot_member_data:
				wrong_input_id.append(f"💥{input_regist_data[2]}")
				#return await ctx.send(f"```루팅자 [{input_regist_data[2]}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")

		check_member_data = list(self.member_db.find())
		for game_id in check_member_data:
			check_member_list.append(game_id['game_ID'])

		for game_id in input_regist_data[3:]:
			if game_id not in check_member_list:
				wrong_input_id.append(game_id)

		if len(wrong_input_id) > 0:
			return await ctx.send(f"```[{', '.join(wrong_input_id)}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")
		
		input_time : datetime = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		insert_data : dict = {}
		insert_data = {"regist_ID":str(ctx.author.id),
					"regist":member_data["game_ID"],
					"getdate":input_time,
					"boss":input_regist_data[0],
					"item":input_regist_data[1],
					"toggle":input_regist_data[2],
					"toggle_ID":str(loot_member_data["_id"]),
					"itemstatus":"미판매",
					"price":0,
					"each_price":0,
					"before_jungsan_ID":sorted(list(set(input_regist_data[3:]))),
					"after_jungsan_ID":[],
					"modifydate":input_time,
					"gulid_money_insert":gulid_money_insert_check,
					"bank_money_insert":False,
					"ladder_check":False,
					"image_url":tmp_image_url
					}
		
		# "_id" : int = 순번
		# "regist_ID" : str = 등록자ID
		# "regist" : str = 등록자 겜 ID
		# "getdate" : datetime = 등록날짜
		# "boss" : str = 보스명
		# "item" : str = 아이템명
		# "toggle" : str = 루팅자 게임 ID
		# "toggle_ID" : str = 루팅자ID
		# "itemstatus" : str = 아이템상태(미판매, 분배중, 분배완료)
		# "price" : int = 가격
		# "each_price" : int = 분배가격
		# "before_jungsan_ID" : list = 참석명단(분배전)
		# "after_jungsan_ID" : list = 참석명단(분배후)
		# "modifydate" : datetime = 수정날짜
		# "gulid_money_insert" : bool = 혈비등록여부
		# "bank_money_insert" : bool = 은행입금여부
		# "ladder_check":False
		# "image_url":이미지 url

		embed = discord.Embed(
				title = "📜 등록 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 일시 ]", value = f"```{insert_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{insert_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{insert_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{insert_data['toggle']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(insert_data['before_jungsan_ID'])}```")
		await ctx.send(embed = embed)

		data_regist_warning_message = await ctx.send(f"**입력하신 등록 내역을 확인해 보세요!**\n**등록 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 등록이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]

		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **등록**를 취소합니다!")

		if str(reaction) == "⭕":
			self.index_value += 1
			result = self.jungsan_db.update_one({"_id":self.index_value}, {"$set":insert_data}, upsert = True)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 등록 실패.") 

			return await ctx.send(f"📥 **[ 순번 : {self.index_value} ]** 정산 등록 완료! 📥")
		else:
			return await ctx.send(f"**등록**이 취소되었습니다.\n")

	################ 분배뽑기등록 ################ 
	@commands.command(name=commandSetting[52][0], aliases=commandSetting[52][1:])
	async def ladder_regist_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[52][0]} [보스명] [아이템명] [루팅자] [뽑을인원] [참여자1] [참여자2]...** 양식으로 등록 해주세요")

		tmp_args : str = ""
		tmp_image_url : str = ""

		if args.find("https://") != -1:
			tmp_data = args.split("https://")
			tmp_args = tmp_data[0]
			tmp_image_url = f"https://{tmp_data[1]}"
		else:
			tmp_args = args
		
		input_regist_data : list = tmp_args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data < 5:
			return await ctx.send(f"**{commandSetting[52][0]} [보스명] [아이템명] [루팅자] [뽑을인원] [참여자1] [참여자2]...** 양식으로 등록 해주세요")

		check_member_data : list = []
		check_member_list : list = []
		wrong_input_id : list = []
		gulid_money_insert_check : bool = False
		loot_member_data : dict = {}

		if input_regist_data[2] == "혈비":
			gulid_money_insert_check = True
			loot_member_data = {"_id":ctx.author.id}
		else:
			gulid_money_insert_check = False
			loot_member_data = self.member_db.find_one({"game_ID":input_regist_data[2]})
			if not loot_member_data:
				wrong_input_id.append(f"💥{input_regist_data[2]}")
				#return await ctx.send(f"```루팅자 [{input_regist_data[2]}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")

		try:
			ladder_num = int(input_regist_data[3])
		except ValueError:
			return await ctx.send(f"**[뽑을인원]**은 숫자로 입력해주세요")

		tmp_before_jungsan_ID : list = []
		tmp_before_jungsan_ID = input_regist_data[4:]
		# tmp_before_jungsan_ID = list(set(input_regist_data[4:])) # 중복제거
		
		if ladder_num <= 0:
			return await ctx.send(f"**[뽑을인원]**이 0보다 작거나 같습니다. 재입력 해주세요")

		if ladder_num >= len(input_regist_data[4:]):
			return await ctx.send(f"**[뽑을인원]**이 총 인원과 같거나 많습니다. 재입력 해주세요")

		check_member_data = list(self.member_db.find())
		for game_id in check_member_data:
			check_member_list.append(game_id['game_ID'])

		for game_id in input_regist_data[4:]:
			if game_id not in check_member_list:
				wrong_input_id.append(game_id)

		if len(wrong_input_id) > 0:
			return await ctx.send(f"```[{', '.join(wrong_input_id)}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")

		result_before_jungsan_ID : list = []

		for _ in range(ladder_num + 5):
			random.shuffle(tmp_before_jungsan_ID)

		for _ in range(ladder_num + 5):
			result_before_jungsan_ID = random.sample(tmp_before_jungsan_ID, ladder_num)
		
		input_time : datetime = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		insert_data : dict = {}
		insert_data = {"regist_ID":str(ctx.author.id),
					"regist":member_data["game_ID"],
					"getdate":input_time,
					"boss":input_regist_data[0],
					"item":input_regist_data[1],
					"toggle":input_regist_data[2],
					"toggle_ID":str(loot_member_data["_id"]),
					"itemstatus":"미판매",
					"price":0,
					"each_price":0,
					"before_jungsan_ID":sorted(result_before_jungsan_ID),
					"after_jungsan_ID":[],
					"modifydate":input_time,
					"gulid_money_insert":gulid_money_insert_check,
					"bank_money_insert":False,
					"ladder_check":True,
					"image_url":tmp_image_url
					}

		embed = discord.Embed(
				title = "📜 뽑기등록 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 일시 ]", value = f"```{insert_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{insert_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{insert_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{insert_data['toggle']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(insert_data['before_jungsan_ID'])}```")
		await ctx.send(embed = embed)

		data_regist_warning_message = await ctx.send(f"**입력하신 등록 내역을 확인해 보세요!**\n**등록 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 등록이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]

		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **뽑기등록**를 취소합니다!")

		if str(reaction) == "⭕":
			self.index_value += 1
			result = self.jungsan_db.update_one({"_id":self.index_value}, {"$set":insert_data}, upsert = True)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 뽑기등록 실패.") 

			return await ctx.send(f"📥 **[ 순번 : {self.index_value} ]** 정산 뽑기등록 완료! 📥")
		else:
			return await ctx.send(f"**뽑기등록**이 취소되었습니다.\n")

	################ 전체내역확인 ################ 
	@is_manager()
	@commands.command(name=commandSetting[43][0], aliases=commandSetting[43][1:])
	async def all_distribute_check(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		visual_flag : int = 0

		jungsan_document : list = []
		if not args:
			jungsan_document : list = list(self.jungsan_db.find({}))
		else:
			input_distribute_all_finish : list = args.split()
			
			if input_distribute_all_finish[0] == "상세":
				visual_flag = 1
				del(input_distribute_all_finish[0])
			
			len_input_distribute_all_finish = len(input_distribute_all_finish)

			if len_input_distribute_all_finish == 0:
				jungsan_document : list = list(self.jungsan_db.find({}))
			elif len_input_distribute_all_finish != 2:
				return await ctx.send(f"**{commandSetting[43][0]} (상세) [검색조건] [검색값]** 형식으로 입력 해주세요! **[검색조건]**은 **[순번, 보스명, 아이템, 루팅, 등록, 날짜, 분배상태]** 일곱가지 중 **1개**를 입력 하셔야합니다!")
			else:
				if input_distribute_all_finish[0] == "순번":
					try:
						input_distribute_all_finish[1] = int(input_distribute_all_finish[1])
					except:
						return await ctx.send(f"**[순번] [검색값]**은 \"숫자\"로 입력 해주세요!")
					jungsan_document : dict = self.jungsan_db.find_one({"_id":input_distribute_all_finish[1]})
					if not jungsan_document:
						return await ctx.send(f"{ctx.author.mention}님! 등록된 정산 목록이 없습니다.")
					embed = get_detail_embed(jungsan_document)
					try:
						return await ctx.send(embed = embed)
					except Exception:
						embed.add_field(name = "🚫  이미지 링크 확인 필요  🚫", value = f"```저장된 이미지가 삭제됐습니다.```")
						embed.set_image(url = "")
						result1 = self.jungsan_db.update_one({"_id":input_distribute_all_finish[1]}, {"$set":{"image_url":""}}, upsert = True)
						if result1.raw_result["nModified"] < 1 and "upserted" not in result1.raw_result:
							return await ctx.send(f"{ctx.author.mention}, 정산 등록 실패.") 
						return await ctx.send(embed = embed)
				elif input_distribute_all_finish[0] == "보스명":
					jungsan_document : list = list(self.jungsan_db.find({"boss":input_distribute_all_finish[1]}))
				elif input_distribute_all_finish[0] == "아이템":
					jungsan_document : list = list(self.jungsan_db.find({"item":input_distribute_all_finish[1]}))
				elif input_distribute_all_finish[0] == "루팅":
					jungsan_document : list = list(self.jungsan_db.find({"toggle":input_distribute_all_finish[1]}))
				elif input_distribute_all_finish[0] == "등록":
					jungsan_document : list = list(self.jungsan_db.find({"regist":input_distribute_all_finish[1]}))
				elif input_distribute_all_finish[0] == "날짜":
					try:
						start_search_date : str = datetime.datetime.now().replace(year = int(input_distribute_all_finish[1][:4]), month = int(input_distribute_all_finish[1][5:7]), day = int(input_distribute_all_finish[1][8:10]), hour = 0, minute = 0, second = 0)
						end_search_date : str = start_search_date + datetime.timedelta(days = 1)
					except:
						return await ctx.send(f"**[날짜] [검색값]**은 0000-00-00 형식으로 입력 해주세요!")
					jungsan_document : list = list(self.jungsan_db.find({"getdate":{"$gte":start_search_date, "$lt":end_search_date}}))
				elif input_distribute_all_finish[0] == "분배상태":
					if input_distribute_all_finish[1] == "분배중":
						jungsan_document : list = list(self.jungsan_db.find({"itemstatus" : "분배중"}))
					elif input_distribute_all_finish[1] == "미판매":
						jungsan_document : list = list(self.jungsan_db.find({"itemstatus" : "미판매"}))
					else:
						return await ctx.send(f"**[분배상태] [검색값]**은 \"미판매\" 혹은 \"분배중\"로 입력 해주세요!")
				else:
					return await ctx.send(f"**[검색조건]**이 잘못 됐습니다. **[검색조건]**은 **[순번, 보스명, 아이템, 루팅, 등록, 날짜, 분배상태]** 일곱가지 중 **1개**를 입력 하셔야합니다!")
		
		if len(jungsan_document) == 0:
			return await ctx.send(f"{ctx.author.mention}님! 등록된 정산 목록이 없습니다.")

		total_distribute_money : int = 0
		embed_list : list = []
		embed_limit_checker : int = 0
		embed_cnt : int = 0
		detail_title_info	: str = ""
		detail_info	: str = ""
		
		embed = discord.Embed(
					title = f"📜 전체 등록 내역",
					description = "",
					color=0x00ff00
					)
		embed_list.append(embed)
		for jungsan_data in jungsan_document:
			embed_limit_checker += 1
			if embed_limit_checker == 20:
				embed_limit_checker = 0
				embed_cnt += 1
				tmp_embed = discord.Embed(
					title = "",
					description = "",
					color=0x00ff00
					)
				embed_list.append(tmp_embed)

			if jungsan_data['gulid_money_insert']:
				if jungsan_data['itemstatus'] == "미판매":
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | 혈비적립예정\n[ 등록자 : {jungsan_data['regist']} ]"
					detail_info = f"```fix\n[ 혈비적립 ]```"
				else:
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | 혈비적립완료\n[ 등록자 : {jungsan_data['regist']} ]"
					detail_info = f"~~```fix\n[ 혈비적립 ]```~~"
			elif jungsan_data['bank_money_insert']:
				detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | 은행저축완료\n[ 등록자 : {jungsan_data['regist']} ]"
				detail_info = f"~~```fix\n[ 은행저축 ]```~~"
			else:
				if jungsan_data['itemstatus'] == "분배중":
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | {jungsan_data['itemstatus']} : 1인당 💰{jungsan_data['each_price']}\n[ 등록자 : {jungsan_data['regist']} ]"
					if visual_flag == 0:
						detail_info = f"```fix\n[ 분배중 ] : {len(jungsan_data['before_jungsan_ID'])}명   [ 분배완료 ] : {len(jungsan_data['after_jungsan_ID'])}명```"
					else:
						detail_info = f"```diff\n+ 분 배 중 : {len(jungsan_data['before_jungsan_ID'])}명 (💰{len(jungsan_data['before_jungsan_ID'])*jungsan_data['each_price']})\n{', '.join(jungsan_data['before_jungsan_ID'])}\n- 분배완료 : {len(jungsan_data['after_jungsan_ID'])}명  (💰{len(jungsan_data['after_jungsan_ID'])*jungsan_data['each_price']})\n{', '.join(jungsan_data['after_jungsan_ID'])}```"
					total_distribute_money += len(jungsan_data['before_jungsan_ID'])*int(jungsan_data['each_price'])
				elif jungsan_data['itemstatus'] == "미판매":
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | {jungsan_data['itemstatus']}\n[ 등록자 : {jungsan_data['regist']} ]"
					if visual_flag == 0:
						detail_info = f"```ini\n[ 참여자 ] : {len(jungsan_data['before_jungsan_ID'])}명```"
					else:
						detail_info = f"```ini\n[ 참여자 ] : {len(jungsan_data['before_jungsan_ID'])}명\n{', '.join(jungsan_data['before_jungsan_ID'])}```"
				else:
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | {jungsan_data['itemstatus']} | 💰~~{jungsan_data['price']}~~\n[ 등록자 : {jungsan_data['regist']} ]"
					if visual_flag == 0:
						detail_info = f"~~```yaml\n[ 분배완료 ] : {len(jungsan_data['after_jungsan_ID'])}명```~~"
					else:
						detail_info = f"~~```yaml\n[ 분배완료 ] : {len(jungsan_data['after_jungsan_ID'])}명\n{', '.join(jungsan_data['after_jungsan_ID'])}```~~"

			if 'image_url' in jungsan_data.keys():
				if jungsan_data['image_url'] != "":
					detail_title_info += " 📸"
			
			if jungsan_data['ladder_check']:
				detail_title_info += " 🌟"

			embed_list[embed_cnt].add_field(name = detail_title_info,
							value = detail_info,
							inline = False)

		if len(embed_list) > 1:
			for embed_data in embed_list:
				await asyncio.sleep(0.1)
				await ctx.send(embed = embed_data)
		else:
			await ctx.send(embed = embed)

		embed1 = discord.Embed(
			title = f"총 정산 금액 : 💰 {str(total_distribute_money)}",
			description = "",
			color=0x00ff00
			)
		return await ctx.send(embed = embed1)

	################ 등록내역확인 ################ 
	@commands.command(name=commandSetting[13][0], aliases=commandSetting[13][1:])
	async def distribute_check(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		visual_flag : int = 0

		jungsan_document : list = []
		if not args:
			jungsan_document : list = list(self.jungsan_db.find({"regist_ID":str(ctx.author.id)}))
		else:
			input_distribute_all_finish : list = args.split()
			
			if input_distribute_all_finish[0] == "상세":
				visual_flag = 1
				del(input_distribute_all_finish[0])
			
			len_input_distribute_all_finish = len(input_distribute_all_finish)

			if len_input_distribute_all_finish == 0:
				jungsan_document : list = list(self.jungsan_db.find({"regist_ID":str(ctx.author.id)}))
			elif len_input_distribute_all_finish != 2:
				return await ctx.send(f"**{commandSetting[13][0]} (상세) [검색조건] [검색값]** 형식으로 입력 해주세요! **[검색조건]**은 **[순번, 보스명, 아이템, 날짜, 분배상태]** 다섯가지 중 **1개**를 입력 하셔야합니다!")
			else:
				if input_distribute_all_finish[0] == "순번":
					try:
						input_distribute_all_finish[1] = int(input_distribute_all_finish[1])
					except:
						return await ctx.send(f"**[순번] [검색값]**은 \"숫자\"로 입력 해주세요!")
					jungsan_document : dict = self.jungsan_db.find_one({"regist_ID":str(ctx.author.id), "_id":input_distribute_all_finish[1]})
					if not jungsan_document:
						return await ctx.send(f"{ctx.author.mention}님! 등록된 정산 목록이 없습니다.")
					embed = get_detail_embed(jungsan_document)
					try:
						return await ctx.send(embed = embed)
					except Exception:
						embed.add_field(name = "🚫  이미지 링크 확인 필요  🚫", value = f"```저장된 이미지가 삭제됐습니다.```")
						embed.set_image(url = "")
						result1 = self.jungsan_db.update_one({"_id":input_distribute_all_finish[1]}, {"$set":{"image_url":""}}, upsert = True)
						if result1.raw_result["nModified"] < 1 and "upserted" not in result1.raw_result:
							return await ctx.send(f"{ctx.author.mention}, 정산 등록 실패.") 
						return await ctx.send(embed = embed)
				elif input_distribute_all_finish[0] == "보스명":
					jungsan_document : list = list(self.jungsan_db.find({"regist_ID":str(ctx.author.id), "boss":input_distribute_all_finish[1]}))
				elif input_distribute_all_finish[0] == "아이템":
					jungsan_document : list = list(self.jungsan_db.find({"regist_ID":str(ctx.author.id), "item":input_distribute_all_finish[1]}))
				elif input_distribute_all_finish[0] == "날짜":
					try:
						start_search_date : str = (datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))).replace(year = int(input_distribute_all_finish[1][:4]), month = int(input_distribute_all_finish[1][5:7]), day = int(input_distribute_all_finish[1][8:10]), hour = 0, minute = 0, second = 0)
						end_search_date : str = start_search_date + datetime.timedelta(days = 1)
					except:
						return await ctx.send(f"**[날짜] [검색값]**은 0000-00-00 형식으로 입력 해주세요!")
					jungsan_document : list = list(self.jungsan_db.find({"regist_ID":str(ctx.author.id), "getdate":{"$gte":start_search_date, "$lt":end_search_date}}))
				elif input_distribute_all_finish[0] == "분배상태":
					if input_distribute_all_finish[1] == "분배중":
						jungsan_document : list = list(self.jungsan_db.find({"regist_ID":str(ctx.author.id), "itemstatus" : "분배중"}))
					elif input_distribute_all_finish[1] == "미판매":
						jungsan_document : list = list(self.jungsan_db.find({"regist_ID":str(ctx.author.id), "itemstatus" : "미판매"}))
					else:
						return await ctx.send(f"**[분배상태] [검색값]**은 \"미판매\" 혹은 \"분배중\"로 입력 해주세요!")
				else:
					return await ctx.send(f"**[검색조건]**이 잘못 됐습니다. **[검색조건]**은 **[순번, 보스명, 아이템, 날짜, 분배상태]** 다섯가지 중 **1개**를 입력 하셔야합니다!")
		
		if len(jungsan_document) == 0:
			return await ctx.send(f"{ctx.author.mention}님! 등록된 정산 목록이 없습니다.")

		total_distribute_money : int = 0
		embed_list : list = []
		embed_limit_checker : int = 0
		embed_cnt : int = 0
		detail_title_info	: str = ""
		detail_info	: str = ""
		
		embed = discord.Embed(
					title = f"📜 [{member_data['game_ID']}]님 등록 내역",
					description = "",
					color=0x00ff00
					)
		embed_list.append(embed)
		for jungsan_data in jungsan_document:
			embed_limit_checker += 1
			if embed_limit_checker == 20:
				embed_limit_checker = 0
				embed_cnt += 1
				tmp_embed = discord.Embed(
					title = "",
					description = "",
					color=0x00ff00
					)
				embed_list.append(tmp_embed)

			if jungsan_data['gulid_money_insert']:
				if jungsan_data['itemstatus'] == "미판매":
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | 혈비적립예정"
					detail_info = f"```fix\n[ 혈비적립 ]```"
				else:
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | 혈비적립완료"
					detail_info = f"~~```fix\n[ 혈비적립 ]```~~"
			elif jungsan_data['bank_money_insert']:
				detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | 은행저축완료"
				detail_info = f"~~```fix\n[ 은행저축 ]```~~"
			else:
				if jungsan_data['itemstatus'] == "분배중":
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | {jungsan_data['itemstatus']} : 1인당 💰{jungsan_data['each_price']}"
					if visual_flag == 0:
						detail_info = f"```fix\n[ 분배중 ] : {len(jungsan_data['before_jungsan_ID'])}명   [ 분배완료 ] : {len(jungsan_data['after_jungsan_ID'])}명```"
					else:
						detail_info = f"```diff\n+ 분 배 중 : {len(jungsan_data['before_jungsan_ID'])}명 (💰{len(jungsan_data['before_jungsan_ID'])*jungsan_data['each_price']})\n{', '.join(jungsan_data['before_jungsan_ID'])}\n- 분배완료 : {len(jungsan_data['after_jungsan_ID'])}명  (💰{len(jungsan_data['after_jungsan_ID'])*jungsan_data['each_price']})\n{', '.join(jungsan_data['after_jungsan_ID'])}```"
					total_distribute_money += len(jungsan_data['before_jungsan_ID'])*int(jungsan_data['each_price'])
				elif jungsan_data['itemstatus'] == "미판매":
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | {jungsan_data['itemstatus']}"
					if visual_flag == 0:
						detail_info = f"```ini\n[ 참여자 ] : {len(jungsan_data['before_jungsan_ID'])}명```"
					else:
						detail_info = f"```ini\n[ 참여자 ] : {len(jungsan_data['before_jungsan_ID'])}명\n{', '.join(jungsan_data['before_jungsan_ID'])}```"
				else:
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | {jungsan_data['itemstatus']} | 💰~~{jungsan_data['price']}~~"
					if visual_flag == 0:
						detail_info = f"~~```yaml\n[ 분배완료 ] : {len(jungsan_data['after_jungsan_ID'])}명```~~"
					else:
						detail_info = f"~~```yaml\n[ 분배완료 ] : {len(jungsan_data['after_jungsan_ID'])}명\n{', '.join(jungsan_data['after_jungsan_ID'])}```~~"

			if 'image_url' in jungsan_data.keys():
				if jungsan_data['image_url'] != "":
					detail_title_info += " 📸"
			
			if jungsan_data['ladder_check']:
				detail_title_info += " 🌟"

			embed_list[embed_cnt].add_field(name = detail_title_info,
							value = detail_info,
							inline = False)

		if len(embed_list) > 1:
			for embed_data in embed_list:
				await asyncio.sleep(0.1)
				await ctx.send(embed = embed_data)
		else:
			await ctx.send(embed = embed)

		embed1 = discord.Embed(
			title = f"총 정산 금액 : 💰 {str(total_distribute_money)}",
			description = "",
			color=0x00ff00
			)
		return await ctx.send(embed = embed1)

	################ 등록내역수정 ################ 
	@commands.command(name=commandSetting[14][0], aliases=commandSetting[14][1:])
	async def modify_regist_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[14][0]} [순번] [보스명] [아이템명] [루팅자] [참여자1] [참여자2]...** 양식으로 등록 해주세요")
		
		input_regist_data : list = args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data < 5:
			return await ctx.send(f"**{commandSetting[14][0]} [순번] [보스명] [아이템명] [루팅자] [참여자1] [참여자2]...** 양식으로 등록 해주세요")
		
		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"_id":int(input_regist_data[0]), "itemstatus":"미판매"})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"_id":int(input_regist_data[0]), "regist_ID":str(member_data['_id']), "itemstatus":"미판매"})
		
		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]**중이 아니거나 없습니다. **[ {commandSetting[13][0]} ]** 명령을 통해 확인해주세요.\n※정산 등록 내역 수정은 **[ 분배상태 ]**가 **[ 미판매 ]** 중인 등록건만 수정 가능합니다!")

		del(input_regist_data[0])

		check_member_data : list = []
		check_member_list : list = []
		check_member_id_list : list = []
		wrong_input_id : list = []
		gulid_money_insert_check : bool = False
		loot_member_data : dict = {}

		if input_regist_data[2] == "혈비":
			gulid_money_insert_check = True
			loot_member_data["_id"] = ctx.author.id
		else:
			gulid_money_insert_check = False
			loot_member_data = self.member_db.find_one({"game_ID":input_regist_data[2]})
			if not loot_member_data:
				wrong_input_id.append(f"💥{input_regist_data[2]}")
				#return await ctx.send(f"```루팅자 [{input_regist_data[2]}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")

		check_member_data = list(self.member_db.find())
		for game_id in check_member_data:
			check_member_list.append(game_id['game_ID'])
			if game_id['game_ID'] == input_regist_data[2]:
				loot_member_data["_id"] = game_id['_id']

		for game_id in input_regist_data[3:]:
			if game_id not in check_member_list:
				wrong_input_id.append(game_id)
		
		if len(wrong_input_id) > 0:
			return await ctx.send(f"```[{', '.join(wrong_input_id)}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")
		
		input_time : datetime = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		insert_data : dict = {}
		insert_data = jungsan_data.copy()
		insert_data["boss"] = input_regist_data[0]
		insert_data["item"] = input_regist_data[1]
		insert_data["toggle"] = input_regist_data[2]
		insert_data["toggle_ID"] = str(loot_member_data["_id"])
		insert_data["before_jungsan_ID"] = list(set(input_regist_data[3:]))
		insert_data["modifydate"] = input_time
		insert_data["gulid_money_insert"] = gulid_money_insert_check
		
		embed = discord.Embed(
				title = "📜 수정 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		if jungsan_data['boss'] == insert_data['boss']:
			embed.add_field(name = "[ 보스 ]", value = f"```{insert_data['boss']}```")
		else:
			embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']} → {insert_data['boss']}```")
		if jungsan_data['item'] == insert_data['item']:
			embed.add_field(name = "[ 아이템 ]", value = f"```{insert_data['item']}```")
		else:
			embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']} → {insert_data['item']}```")
		if jungsan_data['toggle'] == insert_data['toggle']:
			embed.add_field(name = "[ 루팅 ]", value = f"```{insert_data['toggle']}```")
		else:
			embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']} → {insert_data['toggle']}```")
		if jungsan_data['before_jungsan_ID'] == insert_data['before_jungsan_ID']:
			embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(insert_data['before_jungsan_ID'])}```")
		else:
			embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID'])} → {', '.join(insert_data['before_jungsan_ID'])}```")
		embed.set_footer(text = f"{insert_data['modifydate'].strftime('%y-%m-%d %H:%M:%S')} 수정!")
		await ctx.send(embed = embed)

		data_regist_warning_message = await ctx.send(f"**입력하신 수정 내역을 확인해 보세요!**\n**수정 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 수정이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **수정**을 취소합니다!")

		if str(reaction) == "⭕":
			result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":insert_data}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 등록 내역 수정 실패.") 

			return await ctx.send(f"📥 정산 등록 내역 수정 완료! 📥")
		else:
			return await ctx.send(f"**수정**이 취소되었습니다.\n")

	################ 등록삭제 ################ 
	@commands.command(name=commandSetting[15][0], aliases=commandSetting[15][1:])
	async def distribute_delete(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[15][0]} [순번]** 양식으로 확인 해주세요")

		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(args)}, {"$or" : [{"itemstatus" : "분배완료"}, {"itemstatus" : "미판매"}]}]})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"regist_ID":str(ctx.author.id)}, {"_id":int(args)}, {"$or" : [{"itemstatus" : "분배완료"}, {"itemstatus" : "미판매"}]}]})

		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 분배중 ]**이거나 없습니다. **[ {commandSetting[13][0]} ]** 명령을 통해 확인해주세요.\n※정산 등록 내역 삭제는 **[ 분배상태 ]**가 **[ 미판매/분배완료 ]** 인 등록건만 수정 가능합니다!")
		
		embed = discord.Embed(
					title = "⚠️☠️⚠️ 삭제 내역 ⚠️☠️⚠️",
					description = "",
					color=0x00ff00
					)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']}```")
		embed.add_field(name = "[ 상태 ]", value = f"```{jungsan_data['itemstatus']}```")
		embed.add_field(name = "[ 판매금 ]", value = f"```{jungsan_data['price']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID']+jungsan_data['after_jungsan_ID'])}```")
		await ctx.send(embed = embed)
		
		delete_warning_message = await ctx.send(f"**등록 내역을 삭제하시면 다시는 복구할 수 없습니다. 정말로 삭제하시겠습니까?**\n**삭제 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 삭제가 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await delete_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == delete_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await delete_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **삭제**를 취소합니다!")

		if str(reaction) == "⭕":
			self.jungsan_db.delete_one({"_id":int(args)})
			return await ctx.send(f"☠️ 정산 내역 삭제 완료! ☠️")
		else:
			return await ctx.send(f"**삭제**가 취소되었습니다.\n")

	################ 루팅자 ################ 
	@commands.command(name=commandSetting[16][0], aliases=commandSetting[16][1:])
	async def loot_distribute_check(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		visual_flag : int = 0

		jungsan_document : list = []
		if not args:
			jungsan_document : list = list(self.jungsan_db.find({"toggle_ID":str(ctx.author.id)}))
		else:
			input_distribute_all_finish : list = args.split()
			
			if input_distribute_all_finish[0] == "상세":
				visual_flag = 1
				del(input_distribute_all_finish[0])
			
			len_input_distribute_all_finish = len(input_distribute_all_finish)

			if len_input_distribute_all_finish == 0:
				jungsan_document : list = list(self.jungsan_db.find({"toggle_ID":str(ctx.author.id)}))
			elif len_input_distribute_all_finish != 2:
				return await ctx.send(f"**{commandSetting[16][0]} (상세) [검색조건] [검색값]** 형식으로 입력 해주세요! **[검색조건]**은 **[순번, 보스명, 아이템, 날짜, 분배상태]** 다섯가지 중 **1개**를 입력 하셔야합니다!")
			else:
				if input_distribute_all_finish[0] == "순번":
					try:
						input_distribute_all_finish[1] = int(input_distribute_all_finish[1])
					except:
						return await ctx.send(f"**[순번] [검색값]**은 \"숫자\"로 입력 해주세요!")
					jungsan_document : dict = self.jungsan_db.find_one({"toggle_ID":str(ctx.author.id), "_id":input_distribute_all_finish[1]})
					if not jungsan_document:
						return await ctx.send(f"{ctx.author.mention}님! 등록된 정산 목록이 없습니다.")
					embed = get_detail_embed(jungsan_document)
					try:
						return await ctx.send(embed = embed)
					except Exception:
						embed.add_field(name = "🚫  이미지 링크 확인 필요  🚫", value = f"```저장된 이미지가 삭제됐습니다.```")
						embed.set_image(url = "")
						result1 = self.jungsan_db.update_one({"_id":input_distribute_all_finish[1]}, {"$set":{"image_url":""}}, upsert = True)
						if result1.raw_result["nModified"] < 1 and "upserted" not in result1.raw_result:
							return await ctx.send(f"{ctx.author.mention}, 정산 등록 실패.") 
						return await ctx.send(embed = embed)
				elif input_distribute_all_finish[0] == "보스명":
					jungsan_document : list = list(self.jungsan_db.find({"toggle_ID":str(ctx.author.id), "boss":input_distribute_all_finish[1]}))
				elif input_distribute_all_finish[0] == "아이템":
					jungsan_document : list = list(self.jungsan_db.find({"toggle_ID":str(ctx.author.id), "item":input_distribute_all_finish[1]}))
				elif input_distribute_all_finish[0] == "날짜":
					try:
						start_search_date : str = (datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))).replace(year = int(input_distribute_all_finish[1][:4]), month = int(input_distribute_all_finish[1][5:7]), day = int(input_distribute_all_finish[1][8:10]), hour = 0, minute = 0, second = 0)
						end_search_date : str = start_search_date + datetime.timedelta(days = 1)
					except:
						return await ctx.send(f"**[날짜] [검색값]**은 0000-00-00 형식으로 입력 해주세요!")
					jungsan_document : list = list(self.jungsan_db.find({"toggle_ID":str(ctx.author.id), "getdate":{"$gte":start_search_date, "$lt":end_search_date}}))
				elif input_distribute_all_finish[0] == "분배상태":
					if input_distribute_all_finish[1] == "분배중":
						jungsan_document : list = list(self.jungsan_db.find({"toggle_ID":str(ctx.author.id), "itemstatus" : "분배중"}))
					elif input_distribute_all_finish[1] == "미판매":
						jungsan_document : list = list(self.jungsan_db.find({"toggle_ID":str(ctx.author.id), "itemstatus" : "미판매"}))
					else:
						return await ctx.send(f"**[분배상태] [검색값]**은 \"미판매\" 혹은 \"분배중\"로 입력 해주세요!")
				else:
					return await ctx.send(f"**[검색조건]**이 잘못 됐습니다. **[검색조건]**은 **[순번, 보스명, 아이템, 날짜, 분배상태]** 다섯가지 중 **1개**를 입력 하셔야합니다!")
		
		if len(jungsan_document) == 0:
			return await ctx.send(f"{ctx.author.mention}님! 루팅한 정산 목록이 없습니다.")

		total_distribute_money : int = 0
		embed_list : list = []
		embed_limit_checker : int = 0
		embed_cnt : int = 0
		detail_title_info	: str = ""
		detail_info	: str = ""
		
		embed = discord.Embed(
					title = f"📜 [{member_data['game_ID']}]님 루팅 내역",
					description = "",
					color=0x00ff00
					)
		embed_list.append(embed)
		for jungsan_data in jungsan_document:
			embed_limit_checker += 1
			if embed_limit_checker == 20:
				embed_limit_checker = 0
				embed_cnt += 1
				tmp_embed = discord.Embed(
					title = "",
					description = "",
					color=0x00ff00
					)
				embed_list.append(tmp_embed)
			
			if jungsan_data['gulid_money_insert']:
				if jungsan_data['itemstatus'] == "미판매":
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | 혈비적립예정"
					detail_info = f"```fix\n[ 혈비적립 ]```"
				else:
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | 혈비적립완료"
					detail_info = f"~~```fix\n[ 혈비적립 ]```~~"
			elif jungsan_data['bank_money_insert']:
				detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | 은행저축"
				detail_info = f"~~```fix\n[ 은행저축 ]```~~"
			else:			
				if jungsan_data['itemstatus'] == "분배중":
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | {jungsan_data['itemstatus']} : 1인당 💰{jungsan_data['each_price']}"
					if visual_flag == 0:
						detail_info = f"```fix\n[ 분배중 ] : {len(jungsan_data['before_jungsan_ID'])}명   [ 분배완료 ] : {len(jungsan_data['after_jungsan_ID'])}명```"
					else:
						detail_info = f"```diff\n+ 분 배 중 : {len(jungsan_data['before_jungsan_ID'])}명 (💰{len(jungsan_data['before_jungsan_ID'])*jungsan_data['each_price']})\n{', '.join(jungsan_data['before_jungsan_ID'])}\n- 분배완료 : {len(jungsan_data['after_jungsan_ID'])}명  (💰{len(jungsan_data['after_jungsan_ID'])*jungsan_data['each_price']})\n{', '.join(jungsan_data['after_jungsan_ID'])}```"
					total_distribute_money += len(jungsan_data['before_jungsan_ID'])*int(jungsan_data['each_price'])
				elif jungsan_data['itemstatus'] == "미판매":
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | {jungsan_data['itemstatus']}"
					if visual_flag == 0:
						detail_info = f"```ini\n[ 참여자 ] : {len(jungsan_data['before_jungsan_ID'])}명```"
					else:
						detail_info = f"```ini\n[ 참여자 ] : {len(jungsan_data['before_jungsan_ID'])}명\n{', '.join(jungsan_data['before_jungsan_ID'])}```"
				else:
					detail_title_info = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | {jungsan_data['itemstatus']} | 💰~~{jungsan_data['price']}~~"
					if visual_flag == 0:
						detail_info = f"~~```yaml\n[ 분배완료 ] : {len(jungsan_data['after_jungsan_ID'])}명```~~"
					else:
						detail_info = f"~~```yaml\n[ 분배완료 ] : {len(jungsan_data['after_jungsan_ID'])}명\n{', '.join(jungsan_data['after_jungsan_ID'])}```~~"

			if 'image_url' in jungsan_data.keys():
				if jungsan_data['image_url'] != "":
					detail_title_info += " 📸"
			
			if jungsan_data['ladder_check']:
				detail_title_info += " 🌟"

			embed_list[embed_cnt].add_field(name = detail_title_info,
							value = detail_info,
							inline = False)

		if len(embed_list) > 1:
			for embed_data in embed_list:
				await asyncio.sleep(0.1)
				await ctx.send(embed = embed_data)
		else:
			await ctx.send(embed = embed)

		embed1 = discord.Embed(
			title = f"총 정산 금액 : 💰 {str(total_distribute_money)}",
			description = "",
			color=0x00ff00
			)
		return await ctx.send(embed = embed1)

	################ 루팅내역수정 ################ 
	@commands.command(name=commandSetting[17][0], aliases=commandSetting[17][1:])
	async def loot_modify_regist_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[17][0]} [순번] [보스명] [아이템명] [루팅자] [참여자1] [참여자2]...** 양식으로 등록 해주세요")
		
		input_regist_data : list = args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data < 5:
			return await ctx.send(f"**{commandSetting[17][0]} [순번] [보스명] [아이템명] [루팅자] [참여자1] [참여자2]...** 양식으로 등록 해주세요")
		
		jungsan_data : dict = self.jungsan_db.find_one({"_id":int(input_regist_data[0]), "toggle_ID":str(member_data['_id']), "itemstatus":"미판매"})
		
		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 루팅하신 정산 내역이 **[ 미판매 ]**중이 아니거나 없습니다. **[ {commandSetting[16][0]} ]** 명령을 통해 확인해주세요.\n※정산 등록 내역 수정은 **[ 분배상태 ]**가 **[ 미판매 ]** 중인 루팅건만 수정 가능합니다!")

		del(input_regist_data[0])

		check_member_data : list = []
		check_member_list : list = []
		check_member_id_list : list = []
		wrong_input_id : list = []
		gulid_money_insert_check : bool = False
		loot_member_data : dict = {}

		if input_regist_data[2] == "혈비":
			gulid_money_insert_check = True
			loot_member_data["_id"] = ctx.author.id
		else:
			gulid_money_insert_check = False
			loot_member_data = self.member_db.find_one({"game_ID":input_regist_data[2]})
			if not loot_member_data:
				wrong_input_id.append(f"💥{input_regist_data[2]}")
				#return await ctx.send(f"```루팅자 [{input_regist_data[2]}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")

		check_member_data = list(self.member_db.find())
		for game_id in check_member_data:
			check_member_list.append(game_id['game_ID'])
			if game_id['game_ID'] == input_regist_data[2]:
				loot_member_data["_id"] = game_id['_id']

		for game_id in input_regist_data[3:]:
			if game_id not in check_member_list:
				wrong_input_id.append(game_id)

		if len(wrong_input_id) > 0:
			return await ctx.send(f"```[{', '.join(wrong_input_id)}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")
		
		input_time : datetime = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		insert_data : dict = {}
		insert_data = jungsan_data.copy()
		insert_data["boss"] = input_regist_data[0]
		insert_data["item"] = input_regist_data[1]
		insert_data["toggle"] = input_regist_data[2]
		insert_data["toggle_ID"] = str(loot_member_data["_id"])
		insert_data["before_jungsan_ID"] = list(set(input_regist_data[3:]))
		insert_data["modifydate"] = input_time
		insert_data["gulid_money_insert"] = gulid_money_insert_check
		
		embed = discord.Embed(
				title = "📜 수정 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		if jungsan_data['boss'] == insert_data['boss']:
			embed.add_field(name = "[ 보스 ]", value = f"```{insert_data['boss']}```")
		else:
			embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']} → {insert_data['boss']}```")
		if jungsan_data['item'] == insert_data['item']:
			embed.add_field(name = "[ 아이템 ]", value = f"```{insert_data['item']}```")
		else:
			embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']} → {insert_data['item']}```")
		if jungsan_data['toggle'] == insert_data['toggle']:
			embed.add_field(name = "[ 루팅 ]", value = f"```{insert_data['toggle']}```")
		else:
			embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']} → {insert_data['toggle']}```")
		if jungsan_data['before_jungsan_ID'] == insert_data['before_jungsan_ID']:
			embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(insert_data['before_jungsan_ID'])}```")
		else:
			embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID'])} → {', '.join(insert_data['before_jungsan_ID'])}```")
		embed.set_footer(text = f"{insert_data['modifydate'].strftime('%y-%m-%d %H:%M:%S')} 수정!")
		await ctx.send(embed = embed)

		data_regist_warning_message = await ctx.send(f"**입력하신 수정 내역을 확인해 보세요!**\n**수정 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 수정이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **수정**을 취소합니다!")

		if str(reaction) == "⭕":
			result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":insert_data}, upsert = True)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 내역 수정 실패.") 

			return await ctx.send(f"📥 정산 내역 수정 완료! 📥")
		else:
			return await ctx.send(f"**수정**이 취소되었습니다.\n")

	################ 루팅삭제 ################ 
	@commands.command(name=commandSetting[18][0], aliases=commandSetting[18][1:])
	async def loot_distribute_delete(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[18][0]} [순번]** 양식으로 확인 해주세요")

		jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"toggle_ID":str(ctx.author.id)}, {"_id":int(args)}, {"$or" : [{"itemstatus" : "분배완료"}, {"itemstatus" : "미판매"}]}]})

		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 분배중 ]**이거나 없습니다. **[ {commandSetting[16][0]} ]** 명령을 통해 확인해주세요.\n※정산 등록 내역 삭제는 **[ 분배상태 ]**가 **[ 미판매/분배완료 ]** 인 등록건만 수정 가능합니다!")
		
		embed = discord.Embed(
					title = "⚠️☠️⚠️ 삭제 내역 ⚠️☠️⚠️",
					description = "",
					color=0x00ff00
					)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']}```")
		embed.add_field(name = "[ 상태 ]", value = f"```{jungsan_data['itemstatus']}```")
		embed.add_field(name = "[ 판매금 ]", value = f"```{jungsan_data['price']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID']+jungsan_data['after_jungsan_ID'])}```")
		await ctx.send(embed = embed)
		
		delete_warning_message = await ctx.send(f"**정산 내역을 삭제하시면 다시는 복구할 수 없습니다. 정말로 삭제하시겠습니까?**\n**삭제 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 삭제가 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await delete_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == delete_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await delete_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **삭제**를 취소합니다!")

		if str(reaction) == "⭕":
			self.jungsan_db.delete_one({"_id":int(args)})
			return await ctx.send(f"☠️ 정산 내역 삭제 완료! ☠️")
		else:
			return await ctx.send(f"**삭제**가 취소되었습니다.\n")

	################ 보스수정 ################ 
	@commands.command(name=commandSetting[19][0], aliases=commandSetting[19][1:])
	async def modify_regist_boss_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[19][0]} [순번] [보스명]** 양식으로 등록 해주세요")
		
		input_regist_data : list = args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data != 2:
			return await ctx.send(f"**{commandSetting[19][0]} [순번] [보스명]** 양식으로 등록 해주세요")

		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"$or" : [{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		
		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]**중이 아니거나 없습니다. **[ {commandSetting[13][0]}/{commandSetting[16][0]} ]** 명령을 통해 확인해주세요.\n※정산 등록 내역 수정은 **[ 분배상태 ]**가 **[ 미판매 ]** 중인 등록건만 수정 가능합니다!")

		if jungsan_data['boss'] == input_regist_data[1]:
			return await ctx.send(f"```수정하려는 [보스명:{input_regist_data[1]}](이)가 등록된 [보스명]과 같습니다!```")
		
		input_time : datetime = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		insert_data : dict = {}
		insert_data = jungsan_data.copy()
		insert_data["boss"] = input_regist_data[1]
		insert_data["modifydate"] = input_time
		
		embed = discord.Embed(
				title = "📜 수정 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']} → {insert_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']}```")
		embed.add_field(name = "[ 상태 ]", value = f"```{jungsan_data['itemstatus']}```")
		embed.add_field(name = "[ 판매금 ]", value = f"```{jungsan_data['price']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID'])}```")
		embed.set_footer(text = f"{insert_data['modifydate'].strftime('%y-%m-%d %H:%M:%S')} 수정!")
		await ctx.send(embed = embed)

		data_regist_warning_message = await ctx.send(f"**입력하신 수정 내역을 확인해 보세요!**\n**수정 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 수정이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **수정**을 취소합니다!")

		if str(reaction) == "⭕":
			result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":insert_data}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 등록 내역 수정 실패.") 

			return await ctx.send(f"📥 정산 등록 내역 수정 완료! 📥")
		else:
			return await ctx.send(f"**수정**이 취소되었습니다.\n")

	################ 템수정 ################ 
	@commands.command(name=commandSetting[20][0], aliases=commandSetting[20][1:])
	async def modify_regist_item_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[20][0]} [순번] [아이템명]** 양식으로 등록 해주세요")
		
		input_regist_data : list = args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data != 2:
			return await ctx.send(f"**{commandSetting[20][0]} [순번] [아이템명]** 양식으로 등록 해주세요")

		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"$or" : [{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		
		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]**중이 아니거나 없습니다. **[ {commandSetting[13][0]}/{commandSetting[16][0]} ]** 명령을 통해 확인해주세요.\n※정산 등록 내역 수정은 **[ 분배상태 ]**가 **[ 미판매 ]** 중인 등록건만 수정 가능합니다!")

		if jungsan_data['item'] == input_regist_data[1]:
			return await ctx.send(f"```수정하려는 [아이템명:{input_regist_data[1]}](이)가 등록된 [아이템명]과 같습니다!```")
		
		input_time : datetime = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		insert_data : dict = {}
		insert_data = jungsan_data.copy()
		insert_data["item"] = input_regist_data[1]
		insert_data["modifydate"] = input_time
		
		embed = discord.Embed(
				title = "📜 수정 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']} → {insert_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']}```")
		embed.add_field(name = "[ 상태 ]", value = f"```{jungsan_data['itemstatus']}```")
		embed.add_field(name = "[ 판매금 ]", value = f"```{jungsan_data['price']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID'])}```")
		embed.set_footer(text = f"{insert_data['modifydate'].strftime('%y-%m-%d %H:%M:%S')} 수정!")
		await ctx.send(embed = embed)

		data_regist_warning_message = await ctx.send(f"**입력하신 수정 내역을 확인해 보세요!**\n**수정 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 수정이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **수정**을 취소합니다!")

		if str(reaction) == "⭕":
			result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":insert_data}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 등록 내역 수정 실패.") 

			return await ctx.send(f"📥 정산 등록 내역 수정 완료! 📥")
		else:
			return await ctx.send(f"**수정**이 취소되었습니다.\n")

	################ 등록자수정 ################ 
	@is_manager() 
	@commands.command(name=commandSetting[53][0], aliases=commandSetting[53][1:])
	async def modify_regist_user_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[53][0]} [순번] [아이디]** 양식으로 등록 해주세요")
		
		input_regist_data : list = args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data != 2:
			return await ctx.send(f"**{commandSetting[53][0]} [순번] [아이디]** 양식으로 등록 해주세요")

		jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
	
		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]**중이 아니거나 없습니다. **[ {commandSetting[13][0]}/{commandSetting[16][0]} ]** 명령을 통해 확인해주세요.\n※정산 등록 내역 수정은 **[ 분배상태 ]**가 **[ 미판매 ]** 중인 등록건만 수정 가능합니다!")

		if jungsan_data['regist'] == input_regist_data[1]:
			return await ctx.send(f"```수정하려는 [등록자:{input_regist_data[1]}](이)가 등록된 [등록자]와 같습니다!```")

		check_member_data : list = []
		regist_member_data : dict = {}

		regist_member_data = self.member_db.find_one({"game_ID":input_regist_data[1]})
		if not regist_member_data:
			return await ctx.send(f"```등록자 [{input_regist_data[1]}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")

		check_member_data = list(self.member_db.find())
		for game_id in check_member_data:
			if game_id['game_ID'] == input_regist_data[1]:
				regist_member_data["_id"] = game_id['_id']
		
		input_time : datetime = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		insert_data : dict = {}
		insert_data = jungsan_data.copy()
		insert_data["regist"] = input_regist_data[1]
		insert_data["regist_ID"] = str(regist_member_data["_id"])
		insert_data["modifydate"] = input_time

		embed = discord.Embed(
				title = "📜 수정 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 등록 ]", value = f"```{jungsan_data['regist']} → {insert_data['regist']}```")
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']}```")
		embed.add_field(name = "[ 상태 ]", value = f"```{jungsan_data['itemstatus']}```")
		embed.add_field(name = "[ 판매금 ]", value = f"```{jungsan_data['price']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID'])}```")
		embed.set_footer(text = f"{insert_data['modifydate'].strftime('%y-%m-%d %H:%M:%S')} 수정!")
		await ctx.send(embed = embed)

		data_regist_warning_message = await ctx.send(f"**입력하신 수정 내역을 확인해 보세요!**\n**수정 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 수정이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **수정**을 취소합니다!")

		if str(reaction) == "⭕":
			result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":insert_data}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 등록 내역 수정 실패.") 

			return await ctx.send(f"📥 정산 등록 내역 수정 완료! 📥")
		else:
			return await ctx.send(f"**수정**이 취소되었습니다.\n")

	################ 토글수정 ################ 
	@commands.command(name=commandSetting[21][0], aliases=commandSetting[21][1:])
	async def modify_regist_toggle_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[21][0]} [순번] [아이디]** 양식으로 등록 해주세요")
		
		input_regist_data : list = args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data != 2:
			return await ctx.send(f"**{commandSetting[21][0]} [순번] [아이디]** 양식으로 등록 해주세요")
		
		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"$or" : [{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		
		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]**중이 아니거나 없습니다. **[ {commandSetting[13][0]}/{commandSetting[16][0]} ]** 명령을 통해 확인해주세요.\n※정산 등록 내역 수정은 **[ 분배상태 ]**가 **[ 미판매 ]** 중인 등록건만 수정 가능합니다!")

		if jungsan_data['toggle'] == input_regist_data[1]:
			return await ctx.send(f"```수정하려는 [토글자:{input_regist_data[1]}](이)가 등록된 [토글자]과 같습니다!```")

		check_member_data : list = []
		gulid_money_insert_check : bool = False
		loot_member_data : dict = {}

		if input_regist_data[1] == "혈비":
			gulid_money_insert_check = True
			loot_member_data["_id"] = ctx.author.id
		else:
			gulid_money_insert_check = False
			loot_member_data = self.member_db.find_one({"game_ID":input_regist_data[1]})
			if not loot_member_data:
				return await ctx.send(f"```루팅자 [{input_regist_data[1]}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")

		check_member_data = list(self.member_db.find())
		for game_id in check_member_data:
			if game_id['game_ID'] == input_regist_data[1]:
				loot_member_data["_id"] = game_id['_id']
		
		input_time : datetime = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		insert_data : dict = {}
		insert_data = jungsan_data.copy()
		insert_data["toggle"] = input_regist_data[1]
		insert_data["toggle_ID"] = str(loot_member_data["_id"])
		insert_data["gulid_money_insert"] = gulid_money_insert_check
		insert_data["modifydate"] = input_time

		embed = discord.Embed(
				title = "📜 수정 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']} → {insert_data['toggle']}```")
		embed.add_field(name = "[ 상태 ]", value = f"```{jungsan_data['itemstatus']}```")
		embed.add_field(name = "[ 판매금 ]", value = f"```{jungsan_data['price']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID'])}```")
		embed.set_footer(text = f"{insert_data['modifydate'].strftime('%y-%m-%d %H:%M:%S')} 수정!")
		await ctx.send(embed = embed)

		data_regist_warning_message = await ctx.send(f"**입력하신 수정 내역을 확인해 보세요!**\n**수정 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 수정이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **수정**을 취소합니다!")

		if str(reaction) == "⭕":
			result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":insert_data}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 등록 내역 수정 실패.") 

			return await ctx.send(f"📥 정산 등록 내역 수정 완료! 📥")
		else:
			return await ctx.send(f"**수정**이 취소되었습니다.\n")

	################ 참여자추가 ################ 
	@commands.command(name=commandSetting[22][0], aliases=commandSetting[22][1:])
	async def modify_regist_add_member_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[22][0]} [순번] [아이디]** 양식으로 등록 해주세요")
		
		input_regist_data : list = args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data != 2:
			return await ctx.send(f"**{commandSetting[22][0]} [순번] [아이디]** 양식으로 등록 해주세요")
		
		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"$or" : [{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		
		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]**중이 아니거나 없습니다. **[ {commandSetting[13][0]}/{commandSetting[16][0]} ]** 명령을 통해 확인해주세요.\n※정산 등록 내역 수정은 **[ 분배상태 ]**가 **[ 미판매 ]** 중인 등록건만 수정 가능합니다!")

		if input_regist_data[1] in jungsan_data['before_jungsan_ID']:
			return await ctx.send(f"```추가하려는 [참여자:{input_regist_data[1]}](이)가 등록된 [참여자] 목록에 있습니다!```")

		check_member_data : dict = {}

		tmp_member_list : list = []

		check_member_data = self.member_db.find_one({"game_ID":input_regist_data[1]})
		if not check_member_data:
			return await ctx.send(f"```참여자 [{input_regist_data[1]}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")
		
		tmp_member_list = jungsan_data["before_jungsan_ID"].copy()
		tmp_member_list.append(check_member_data["game_ID"])

		input_time : datetime = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		insert_data : dict = {}
		insert_data = jungsan_data.copy()
		insert_data["before_jungsan_ID"] = sorted(tmp_member_list)

		embed = discord.Embed(
				title = "📜 수정 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']}```")
		embed.add_field(name = "[ 상태 ]", value = f"```{jungsan_data['itemstatus']}```")
		embed.add_field(name = "[ 판매금 ]", value = f"```{jungsan_data['price']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID'])} → {', '.join(insert_data['before_jungsan_ID'])}```")
		embed.set_footer(text = f"{insert_data['modifydate'].strftime('%y-%m-%d %H:%M:%S')} 수정!")
		await ctx.send(embed = embed)

		data_regist_warning_message = await ctx.send(f"**입력하신 수정 내역을 확인해 보세요!**\n**수정 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 수정이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **수정**을 취소합니다!")

		if str(reaction) == "⭕":
			result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":insert_data}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 등록 내역 수정 실패.") 

			return await ctx.send(f"📥 정산 등록 내역 수정 완료! 📥")
		else:
			return await ctx.send(f"**수정**이 취소되었습니다.\n")

	################ 참여자삭제 ################ 
	@commands.command(name=commandSetting[23][0], aliases=commandSetting[23][1:])
	async def modify_regist_remove_member_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[23][0]} [순번] [아이디]** 양식으로 등록 해주세요")
		
		input_regist_data : list = args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data != 2:
			return await ctx.send(f"**{commandSetting[23][0]} [순번] [아이디]** 양식으로 등록 해주세요")
		
		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"$or" : [{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		
		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]**중이 아니거나 없습니다. **[ {commandSetting[13][0]}/{commandSetting[16][0]} ]** 명령을 통해 확인해주세요.\n※정산 등록 내역 수정은 **[ 분배상태 ]**가 **[ 미판매 ]** 중인 등록건만 수정 가능합니다!")

		if input_regist_data[1] not in jungsan_data['before_jungsan_ID']:
			return await ctx.send(f"```삭제하려는 [참여자:{input_regist_data[1]}](이)가 등록된 [참여자] 목록에 없습니다!```")

		check_member_data : dict = {}

		tmp_member_list : list = []

		check_member_data = self.member_db.find_one({"game_ID":input_regist_data[1]})
		if not check_member_data:
			return await ctx.send(f"```참여자 [{input_regist_data[1]}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")
		
		tmp_member_list = jungsan_data["before_jungsan_ID"].copy()
		tmp_member_list.remove(check_member_data["game_ID"])

		if len(tmp_member_list) <= 0:
			return await ctx.send(f"```참여자 [{input_regist_data[1]}]를 삭제하면 참여자가 [0]명이 되므로 삭제할 수 없습니다!```")

		input_time : datetime = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		insert_data : dict = {}
		insert_data = jungsan_data.copy()
		insert_data["before_jungsan_ID"] = sorted(tmp_member_list)

		embed = discord.Embed(
				title = "📜 수정 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']}```")
		embed.add_field(name = "[ 상태 ]", value = f"```{jungsan_data['itemstatus']}```")
		embed.add_field(name = "[ 판매금 ]", value = f"```{jungsan_data['price']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID'])} → {', '.join(insert_data['before_jungsan_ID'])}```")
		embed.set_footer(text = f"{insert_data['modifydate'].strftime('%y-%m-%d %H:%M:%S')} 수정!")
		await ctx.send(embed = embed)

		data_regist_warning_message = await ctx.send(f"**입력하신 수정 내역을 확인해 보세요!**\n**수정 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 수정이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **수정**을 취소합니다!")

		if str(reaction) == "⭕":
			result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":insert_data}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 등록 내역 수정 실패.") 

			return await ctx.send(f"📥 정산 등록 내역 수정 완료! 📥")
		else:
			return await ctx.send(f"**수정**이 취소되었습니다.\n")

	################ 이미지 수정 ################ 
	@commands.command(name=commandSetting[50][0], aliases=commandSetting[50][1:])
	async def modify_regist_image_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[50][0]} [순번] [수정이미지 url]** 양식으로 등록 해주세요")
		
		input_regist_data : list = args.split()
		len_input_regist_data = len(input_regist_data)

		if len_input_regist_data != 2:
			return await ctx.send(f"**{commandSetting[50][0]} [순번] [수정이미지 url]** 양식으로 등록 해주세요")
		
		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"$or" : [{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_regist_data[0])}, {"itemstatus":"미판매"}]})
		
		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]**중이 아니거나 없습니다. **[ {commandSetting[13][0]}/{commandSetting[16][0]} ]** 명령을 통해 확인해주세요.\n※정산 등록 내역 수정은 **[ 분배상태 ]**가 **[ 미판매 ]** 중인 등록건만 수정 가능합니다!")

		input_time : datetime = datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))
		insert_data : dict = {}
		insert_data = jungsan_data.copy()
		insert_data["image_url"] = input_regist_data[1]
		insert_data["modifydate"] = input_time
		
		embed = discord.Embed(
				title = "📜 수정 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']}```")
		embed.add_field(name = "[ 상태 ]", value = f"```{jungsan_data['itemstatus']}```")
		embed.add_field(name = "[ 판매금 ]", value = f"```{jungsan_data['price']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID'])}```")
		embed.set_footer(text = f"{insert_data['modifydate'].strftime('%y-%m-%d %H:%M:%S')} 수정!")
		embed.set_image(url = insert_data["image_url"])
		try:
			await ctx.send(embed = embed)
		except Exception:
			embed.add_field(name = "🚫  이미지 링크 확인 필요  🚫", value = f"```저장된 이미지가 삭제됩니다.```")
			insert_data["image_url"] = ""
			embed.set_image(url = insert_data["image_url"])
			await ctx.send(embed = embed)
		
		data_regist_warning_message = await ctx.send(f"**입력하신 수정 내역을 확인해 보세요!**\n**수정 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 수정이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **수정**을 취소합니다!")

		if str(reaction) == "⭕":
			result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":insert_data}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 등록 내역 수정 실패.") 

			return await ctx.send(f"📥 정산 등록 내역 수정 완료! 📥")
		else:
			return await ctx.send(f"**수정**이 취소되었습니다.\n")

	################ 판매입력 ################ 
	@commands.command(name=commandSetting[24][0], aliases=commandSetting[24][1:])
	async def input_sell_price(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[24][0]} [순번] [금액]** 양식으로 입력 해주세요")
		
		input_sell_price_data : list = args.split()
		len_input_sell_price_data = len(input_sell_price_data)

		if len_input_sell_price_data != 2:
			return await ctx.send(f"**{commandSetting[24][0]} [순번] [금액]** 양식으로 입력 해주세요")
		
		try:
			input_sell_price_data[0] = int(input_sell_price_data[0])
			input_sell_price_data[1] = int(input_sell_price_data[1])
		except ValueError:
			return await ctx.send(f"**[순번]** 및 **[금액]**은 숫자로 입력 해주세요")

		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_sell_price_data[0])}, {"itemstatus":"미판매"}]})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"$or" : [{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_sell_price_data[0])}, {"itemstatus":"미판매"}]})

		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]** 중이 아니거나 없습니다. **[ {commandSetting[13][0]} ]** 명령을 통해 확인해주세요")

		result_each_price = int(input_sell_price_data[1]//len(jungsan_data["before_jungsan_ID"]))   # 혈비일 경우 수수로 계산 입력 예정

		if jungsan_data["gulid_money_insert"]:
			after_tax_price : int = int(input_sell_price_data[1]*(1-(basicSetting[7]/100)))
			result_each_price : int = int(after_tax_price//len(jungsan_data["before_jungsan_ID"]))
			result = self.jungsan_db.update_one({"_id":input_sell_price_data[0]}, {"$set":{"price":after_tax_price, "each_price":int(input_sell_price_data[1]), "modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])), "before_jungsan_ID":[], "after_jungsan_ID":sorted(jungsan_data["before_jungsan_ID"]), "itemstatus":"분배완료"}}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 혈비 등록 실패.")
			result_guild = self.guild_db.update_one({"_id":"guild"}, {"$inc":{"guild_money":after_tax_price}}, upsert = True)
			if result_guild.raw_result["nModified"] < 1 and "upserted" not in result_guild.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 혈비 적립 실패.")
			insert_log_data = {
						"in_out_check":True,  # True : 입금, False : 출금
						"log_date":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])),
						"money":str(after_tax_price),
						"member_list":jungsan_data["before_jungsan_ID"],
						"reason":f"[순번:{input_sell_price_data[0]}] - 정산금 혈비 적립"
			}
			result_guild_log = self.guild_db_log.insert_one(insert_log_data)
			return await ctx.send(f"**[ 순번 : {input_sell_price_data[0]} ]**   💰판매금 **[ {after_tax_price} ]**(세율 {basicSetting[7]}% 적용) 혈비 적립 완료!")
		
		result = self.jungsan_db.update_one({"_id":input_sell_price_data[0]}, {"$set":{"price":input_sell_price_data[1], "each_price":result_each_price, "modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])), "itemstatus":"분배중"}}, upsert = False)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 판매 등록 실패.") 			

		return await ctx.send(f"**[ 순번 : {input_sell_price_data[0]} ]**   💰판매금 **[ {input_sell_price_data[1]} ]** 등록 완료! 분배를 시작합니다.")

	################ 뽑기판매입력 ################ 
	@commands.command(name=commandSetting[45][0], aliases=commandSetting[45][1:])
	async def input_ladder_sell_price(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[45][0]} [순번] [금액] [뽑을인원]** 양식으로 입력 해주세요")
		
		input_sell_price_data : list = args.split()
		len_input_sell_price_data = len(input_sell_price_data)

		if len_input_sell_price_data != 3:
			return await ctx.send(f"**{commandSetting[45][0]} [순번] [금액] [뽑을인원]** 양식으로 입력 해주세요")
		
		try:
			input_sell_price_data[0] = int(input_sell_price_data[0])
			input_sell_price_data[1] = int(input_sell_price_data[1])
			input_sell_price_data[2] = int(input_sell_price_data[2])
		except ValueError:
			return await ctx.send(f"**[순번]**, **[금액]** 및 **[뽑을인원]**은 숫자로 입력 해주세요")

		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_sell_price_data[0])}, {"itemstatus":"미판매"}]})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"$or" : [{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_sell_price_data[0])}, {"itemstatus":"미판매"}]})

		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]** 중이 아니거나 없습니다. **[ {commandSetting[45][0]} ]** 명령을 통해 확인해주세요")

		if input_sell_price_data[2] < 1:
			return await ctx.send(f"{ctx.author.mention}님! 추첨인원이 0보다 작거나 같습니다. 재입력 해주세요")

		ladder_check : bool = False
		result_ladder = None

		if len(jungsan_data["before_jungsan_ID"]) > input_sell_price_data[2]:
			tmp_before_jungsan_ID : list = []
			tmp_before_jungsan_ID = jungsan_data["before_jungsan_ID"]
			for _ in range(input_sell_price_data[2] + 5):
				random.shuffle(tmp_before_jungsan_ID)
			for _ in range(input_sell_price_data[2] + 5):
				result_ladder = random.sample(tmp_before_jungsan_ID, input_sell_price_data[2])
			await ctx.send(f"**[ {', '.join(sorted(jungsan_data['before_jungsan_ID']))} ]** 중 **[ {', '.join(sorted(result_ladder))} ]** 당첨! 분배를 시작합니다.")
			result_each_price = int(input_sell_price_data[1]//input_sell_price_data[2])
			ladder_check = True
		else:
			return await ctx.send(f"{ctx.author.mention}님! 추첨인원이 총 인원과 같거나 많습니다. 재입력 해주세요")

		if jungsan_data["gulid_money_insert"]:
			after_tax_price : int = int(input_sell_price_data[1]*(1-(basicSetting[7]/100)))
			result_each_price : int = int(after_tax_price//input_sell_price_data[2])
			result = self.jungsan_db.update_one({"_id":input_sell_price_data[0]}, {"$set":{"price":after_tax_price, "each_price":int(input_sell_price_data[1]), "modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])), "before_jungsan_ID":[], "after_jungsan_ID":sorted(result_ladder), "itemstatus":"분배완료", "ladder_check":ladder_check}}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 혈비 등록 실패.")
			result_guild = self.guild_db.update_one({"_id":"guild"}, {"$inc":{"guild_money":after_tax_price}}, upsert = True)
			if result_guild.raw_result["nModified"] < 1 and "upserted" not in result_guild.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 혈비 적립 실패.")
			insert_log_data = {
						"in_out_check":True,  # True : 입금, False : 출금
						"log_date":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])),
						"money":str(after_tax_price),
						"member_list":sorted(result_ladder),
						"reason":f"[순번:{input_sell_price_data[0]}] - 정산금 혈비 적립"
			}
			result_guild_log = self.guild_db_log.insert_one(insert_log_data)
			return await ctx.send(f"**[ 순번 : {input_sell_price_data[0]} ]**   💰판매금 **[ {after_tax_price} ]**(세율 {basicSetting[7]}% 적용) 혈비 적립 완료!")
		
		result = self.jungsan_db.update_one({"_id":input_sell_price_data[0]}, {"$set":{"price":input_sell_price_data[1], "each_price":result_each_price, "modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])), "before_jungsan_ID":sorted(result_ladder), "itemstatus":"분배중", "ladder_check":ladder_check}}, upsert = False)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 판매 등록 실패.") 			

		return await ctx.send(f"**[ 순번 : {input_sell_price_data[0]} ]**   💰판매금 **[ {input_sell_price_data[1]} ]** 등록 완료! 분배를 시작합니다.")

	################ 판매 취소 ################ 
	@commands.command(name=commandSetting[51][0], aliases=commandSetting[51][1:])
	async def cancel_sell_data(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[51][0]} [순번]** 양식으로 정산 해주세요")

		input_distribute_finish_data = args.split()
		len_input_distribute_finish_data = len(input_distribute_finish_data)

		if len_input_distribute_finish_data != 1:
			return await ctx.send(f"**{commandSetting[51][0]} [순번]** 양식으로 정산 해주세요")

		try:
			input_distribute_finish_data[0] = int(input_distribute_finish_data[0])
		except ValueError:
			return await ctx.send(f"**[순번]**은 숫자로 입력 해주세요")

		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"_id":int(input_distribute_finish_data[0])})
			if jungsan_data["gulid_money_insert"]:
				embed = discord.Embed(
						title = "📜 판매취소 정보(혈비등록건)",
						description = "",
						color=0x00ff00
						)
				embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
				embed.add_field(name = "[ 등록 ]", value = f"```{jungsan_data['regist']}```")
				embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
				embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']}```")
				embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']}```")
				embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']}```")
				embed.add_field(name = "[ 상태 ]", value = f"```{jungsan_data['itemstatus']}```")
				embed.add_field(name = "[ 판매금 ]", value = f"```{jungsan_data['each_price']}```")
				embed.add_field(name = "[ 적립금 ]", value = f"```{jungsan_data['price']}```")
				if jungsan_data["image_url"] != "":
					embed.set_image(url = jungsan_data["image_url"])
				await ctx.send(embed = embed)

				data_regist_warning_message = await ctx.send(f"**판매취소하실 등록 내역을 확인해 보세요!**\n**판매취소 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 판매취소가 취소됩니다.)", tts=False)

				emoji_list : list = ["⭕", "❌"]
				for emoji in emoji_list:
					await data_regist_warning_message.add_reaction(emoji)

				def reaction_check(reaction, user):
					return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

				try:
					reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
				except asyncio.TimeoutError:
					for emoji in emoji_list:
						await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
					return await ctx.send(f"시간이 초과됐습니다. **판매취소**를 취소합니다!")

				if str(reaction) == "⭕":
					result = self.jungsan_db.update_one({"_id":input_distribute_finish_data[0]}, {"$set":{"price":0, "each_price":0, "modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])), "itemstatus":"미판매", "before_jungsan_ID":jungsan_data["after_jungsan_ID"],"after_jungsan_ID":[] }}, upsert = False)
					result_guild = self.guild_db.update_one({"_id":"guild"}, {"$inc":{"guild_money":-jungsan_data["price"]}}, upsert = True)
					if result_guild.raw_result["nModified"] < 1 and "upserted" not in result_guild.raw_result:
						return await ctx.send(f"{ctx.author.mention}, 혈비 적립 실패.")
					insert_log_data = {
								"in_out_check":False,  # True : 입금, False : 출금
								"log_date":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])),
								"money":str(jungsan_data["price"]),
								"member_list":[],
								"reason":f"[순번:{input_distribute_finish_data[0]}] - 판매 취소"
					}
					result_guild_log = self.guild_db_log.insert_one(insert_log_data)
					if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
						return await ctx.send(f"{ctx.author.mention}, 판매 취소 실패.") 

					await ctx.send(f"📥 **[ 순번 : {input_distribute_finish_data[0]} ]** 판매취소 완료! 📥")
					if jungsan_data["ladder_check"]:
						await ctx.send(f"⚠️ `해당 판매`건은 `뽑기판매`건이므로 `참여자 정보를 확인`해야 합니다.")
					return 
				else:
					return await ctx.send(f"**판매취소**가 취소되었습니다.\n")
			else:
				if jungsan_data["itemstatus"] != "분배중" and not jungsan_data["after_jungsan_ID"]:
					jungsan_data = {}
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"$or" : [{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_distribute_finish_data[0])}, {"itemstatus":"분배중"}, {"after_jungsan_ID":[]}]})

		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 분배중 ]**이 아니거나 **[정산]**처리된 인원이 있거나 정산 목록에 없습니다. **[ {commandSetting[13][0]} ]** 명령을 통해 확인해주세요")

		embed = discord.Embed(
				title = "📜 판매취소 정보",
				description = "",
				color=0x00ff00
				)
		embed.add_field(name = "[ 순번 ]", value = f"```{jungsan_data['_id']}```", inline = False)
		embed.add_field(name = "[ 등록 ]", value = f"```{jungsan_data['regist']}```")
		embed.add_field(name = "[ 일시 ]", value = f"```{jungsan_data['getdate'].strftime('%y-%m-%d %H:%M:%S')}```", inline = False)
		embed.add_field(name = "[ 보스 ]", value = f"```{jungsan_data['boss']}```")
		embed.add_field(name = "[ 아이템 ]", value = f"```{jungsan_data['item']}```")
		embed.add_field(name = "[ 루팅 ]", value = f"```{jungsan_data['toggle']}```")
		embed.add_field(name = "[ 상태 ]", value = f"```{jungsan_data['itemstatus']}```")
		embed.add_field(name = "[ 판매금 ]", value = f"```{jungsan_data['price']}```")
		embed.add_field(name = "[ 참여자 ]", value = f"```{', '.join(jungsan_data['before_jungsan_ID'])}```")
		if jungsan_data["image_url"] != "":
			embed.set_image(url = jungsan_data["image_url"])
		await ctx.send(embed = embed)

		data_regist_warning_message = await ctx.send(f"**판매취소하실 등록 내역을 확인해 보세요!**\n**판매취소 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 판매취소가 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await data_regist_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == data_regist_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await data_regist_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **판매취소**를 취소합니다!")

		if str(reaction) == "⭕":
			result = self.jungsan_db.update_one({"_id":input_distribute_finish_data[0]}, {"$set":{"price":0, "each_price":0, "modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])), "itemstatus":"미판매"}}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 판매 취소 실패.") 

			await ctx.send(f"📥 **[ 순번 : {input_distribute_finish_data[0]} ]** 판매취소 완료! 📥")
			if jungsan_data["ladder_check"]:
				await ctx.send(f"⚠️ `해당 판매`건은 `뽑기판매`건이므로 `참여자 정보를 확인`해야 합니다.")
			return
		else:
			return await ctx.send(f"**판매취소**가 취소되었습니다.\n")

	################ 정산 처리 입력 ################ 
	@commands.command(name=commandSetting[25][0], aliases=commandSetting[25][1:])
	async def distribute_finish(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[25][0]} [순번] [아이디]** 양식으로 정산 해주세요")

		input_distribute_finish_data : list = args.split()
		len_input_distribute_finish_data = len(input_distribute_finish_data)

		if len_input_distribute_finish_data != 2:
			return await ctx.send(f"**{commandSetting[25][0]} [순번] [아이디]** 양식으로 정산 해주세요")

		try:
			input_distribute_finish_data[0] = int(input_distribute_finish_data[0])
		except ValueError:
			return await ctx.send(f"**[순번]**은 숫자로 입력 해주세요")

		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_distribute_finish_data[0])}, {"itemstatus":"분배중"}]})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"$or" : [{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_distribute_finish_data[0])}, {"itemstatus":"분배중"}]})

		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 분배중 ]**이 아니거나 없습니다. **[ {commandSetting[13][0]} ]** 명령을 통해 확인해주세요")
		else:
			if input_distribute_finish_data[1] in jungsan_data["after_jungsan_ID"]:
				return await ctx.send(f"**[ {input_distribute_finish_data[1]} ]**님은 **[ 순번 : {input_distribute_finish_data[0]} ]**의 정산 내역에 대하여 이미 💰**[ {jungsan_data['each_price']} ]** 정산 받았습니다!")
			elif input_distribute_finish_data[1] not in jungsan_data["before_jungsan_ID"]:
				return await ctx.send(f"**[ {input_distribute_finish_data[1]} ]**님은 **[ 순번 : {input_distribute_finish_data[0]} ]**의 정산 전 명단에 존재하지 않습니다!")
			else:
				pass
				
		jungsan_data["before_jungsan_ID"].remove(input_distribute_finish_data[1])
		jungsan_data["after_jungsan_ID"].append(input_distribute_finish_data[1])

		len_before_jungsan_data :int = 0
		len_before_jungsan_data = len(jungsan_data["before_jungsan_ID"])

		if len_before_jungsan_data == 0:
			result = self.jungsan_db.update_one({"_id":int(input_distribute_finish_data[0])}, {"$set":{"before_jungsan_ID":sorted(jungsan_data["before_jungsan_ID"]), "after_jungsan_ID":sorted(jungsan_data["after_jungsan_ID"]), "modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])), "itemstatus" : "분배완료"}}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 실패.") 		
			return await ctx.send(f"**[ 순번 : {input_distribute_finish_data[0]} ]** : **[ {input_distribute_finish_data[1]} ]**님 정산 완료!\n**[ 순번 : {input_distribute_finish_data[0]} ]** 분배 완료!🎉")
		else:
			result = self.jungsan_db.update_one({"_id":int(input_distribute_finish_data[0])}, {"$set":{"before_jungsan_ID":sorted(jungsan_data["before_jungsan_ID"]), "after_jungsan_ID":sorted(jungsan_data["after_jungsan_ID"]), "modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))}}, upsert = False)
			if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
				return await ctx.send(f"{ctx.author.mention}, 정산 실패.") 		
			return await ctx.send(f"**[ 순번 : {input_distribute_finish_data[0]} ]** : **[ {input_distribute_finish_data[1]} ]**님 정산 완료!")
	
	################ 정산 처리 취소 ################ 
	@commands.command(name=commandSetting[26][0], aliases=commandSetting[26][1:])
	async def cancel_distribute_finish(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[26][0]} [순번] [아이디]** 양식으로 정산 해주세요")

		input_distribute_finish_data : list = args.split()
		len_input_distribute_finish_data = len(input_distribute_finish_data)

		if len_input_distribute_finish_data != 2:
			return await ctx.send(f"**{commandSetting[26][0]} [순번] [아이디]** 양식으로 정산 해주세요")

		try:
			input_distribute_finish_data[0] = int(input_distribute_finish_data[0])
		except ValueError:
			return await ctx.send(f"**[순번]**은 숫자로 입력 해주세요")

		if "manager" in member_data['permissions']:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_distribute_finish_data[0])}, {"itemstatus":"분배중"}]})
		else:
			jungsan_data : dict = self.jungsan_db.find_one({"$and" : [{"$or" : [{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_distribute_finish_data[0])}, {"itemstatus":"분배중"}]})

		if not jungsan_data:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 분배중 ]**이 아니거나 없습니다. **[ {commandSetting[13][0]} ]** 명령을 통해 확인해주세요")
		else:
			if input_distribute_finish_data[1] in jungsan_data["before_jungsan_ID"]:
				return await ctx.send(f"**[ {input_distribute_finish_data[1]} ]**님은 **[ 순번 : {input_distribute_finish_data[0]} ]**의 정산 내역에 대하여 아직 정산 받지 않았습니다!")
			elif input_distribute_finish_data[1] not in jungsan_data["after_jungsan_ID"]:
				return await ctx.send(f"**[ {input_distribute_finish_data[1]} ]**님은 **[ 순번 : {input_distribute_finish_data[0]} ]**의 정산 후 명단에 존재하지 않습니다!")
			else:
				pass
				
		jungsan_data["after_jungsan_ID"].remove(input_distribute_finish_data[1])
		jungsan_data["before_jungsan_ID"].append(input_distribute_finish_data[1])

		result = self.jungsan_db.update_one({"_id":int(input_distribute_finish_data[0])}, {"$set":{"before_jungsan_ID":sorted(jungsan_data["before_jungsan_ID"]), "after_jungsan_ID":sorted(jungsan_data["after_jungsan_ID"]), "modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))}}, upsert = False)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 정산 취소 실패.") 		
		return await ctx.send(f"**[ 순번 : {input_distribute_finish_data[0]} ]** : **[ {input_distribute_finish_data[1]} ]**님 정산 취소 완료!")

	################ 일괄정산 ################ 
	@commands.command(name=commandSetting[27][0], aliases=commandSetting[27][1:])
	async def distribute_all_finish(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		jungsan_document : list = []

		if not args:
			jungsan_document : list = list(self.jungsan_db.find({"$and" : [{"$or":[{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"itemstatus":"분배중"}]}))
		else:
			input_distribute_all_finish : list = args.split()
			len_input_distribute_all_finish = len(input_distribute_all_finish)

			if len_input_distribute_all_finish != 2:
				return await ctx.send(f"**{commandSetting[27][0]} [검색조건] [검색값]** 형식으로 입력 해주세요! **[검색조건]**은 **[순번, 보스명, 아이템, 날짜]** 다섯가지 중 **1개**를 입력 하셔야합니다!")
			else:
				if input_distribute_all_finish[0] == "순번":
					try:
						input_distribute_all_finish[1] = int(input_distribute_all_finish[1])
					except:
						return await ctx.send(f"**[순번] [검색값]**은 숫자로 입력 해주세요!")
					jungsan_document = list(self.jungsan_db.find({"$and" : [{"$or":[{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":input_distribute_all_finish[1]}, {"itemstatus":"분배중"}]}))
				elif input_distribute_all_finish[0] == "보스명":
					jungsan_document = list(self.jungsan_db.find({"$and" : [{"$or":[{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"boss":input_distribute_all_finish[1]}, {"itemstatus":"분배중"}]}))
				elif input_distribute_all_finish[0] == "아이템":
					jungsan_document = list(self.jungsan_db.find({"$and" : [{"$or":[{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"item":input_distribute_all_finish[1]}, {"itemstatus":"분배중"}]}))
				elif input_distribute_all_finish[0] == "날짜":
					try:
						start_search_date : str = (datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8]))).replace(year = int(input_distribute_all_finish[1][:4]), month = int(input_distribute_all_finish[1][5:7]), day = int(input_distribute_all_finish[1][8:10]), hour = 0, minute = 0, second = 0)
						end_search_date : str = start_search_date + datetime.timedelta(days = 1)
					except:
						return await ctx.send(f"**[날짜] [검색값]**은 0000-00-00 형식으로 입력 해주세요!")
					jungsan_document = list(self.jungsan_db.find({"$and" : [{"$or":[{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"getdate":{"$gte":start_search_date, "$lt":end_search_date}}, {"itemstatus":"분배중"}]}))
				else:
					return await ctx.send(f"**[검색조건]**이 잘못 됐습니다. **[검색조건]**은 **[순번, 보스명, 아이템, 날짜]** 네가지 중 **1개**를 입력 하셔야합니다!")

		if len(jungsan_document) == 0:
			return await ctx.send(f"{ctx.author.mention}님! **[ 분배중 ]**인 정산 내역이 없거나 등록된 정산 내역이 없습니다. **[ {commandSetting[13][0]} ]** 명령을 통해 확인해주세요")

		total_distribute_money : int = 0
		detail_info_ing : str = ""
		embed_list : list = []
		embed_limit_checker : int = 0
		embed_cnt : int = 0
		init_data : dict = {}

		embed = discord.Embed(
					title = f"📜 [{member_data['game_ID']}]님 등록 내역",
					description = "",
					color=0x00ff00
					)

		embed_list.append(embed)
		for jungsan_data in jungsan_document:
			embed_limit_checker += 1
			if embed_limit_checker == 20:
				embed_limit_checker = 0
				embed_cnt += 1
				tmp_embed = discord.Embed(
					title = "",
					description = "",
					color=0x00ff00
					)
				embed_list.append(tmp_embed)
			detail_info_ing = f"```diff\n+ 분 배 중 : {len(jungsan_data['before_jungsan_ID'])}명 (💰{len(jungsan_data['before_jungsan_ID'])*jungsan_data['each_price']})\n{', '.join(jungsan_data['before_jungsan_ID'])}\n- 분배완료 : {len(jungsan_data['after_jungsan_ID'])}명  (💰{len(jungsan_data['after_jungsan_ID'])*jungsan_data['each_price']})\n{', '.join(jungsan_data['after_jungsan_ID'])}```"
			embed_list[embed_cnt].add_field(name = f"[ 순번 : {jungsan_data['_id']} ] | {jungsan_data['getdate'].strftime('%y-%m-%d')} | {jungsan_data['boss']} | {jungsan_data['item']} | {jungsan_data['toggle']} | {jungsan_data['itemstatus']} : 1인당 💰{jungsan_data['each_price']}",
							value = detail_info_ing,
							inline = False)
			total_distribute_money += len(jungsan_data['before_jungsan_ID'])*int(jungsan_data['each_price'])
			init_data[jungsan_data['_id']] = jungsan_data['after_jungsan_ID']

		if len(embed_list) > 1:
			for embed_data in embed_list:
				await asyncio.sleep(0.1)
				await ctx.send(embed = embed_data)
		else:
			await ctx.send(embed = embed)

		embed1 = discord.Embed(
			title = f"일괄정산 예정 금액 : 💰 {str(total_distribute_money)}",
			description = "",
			color=0x00ff00
			)
		await ctx.send(embed = embed1)

		distribute_all_finish_warning_message = await ctx.send(f"**일괄 정산 예정인 등록 내역을 확인해 보세요!**\n**일괄정산 : ⭕ 취소: ❌**\n({basicSetting[5]}초 동안 입력이 없을시 일괄정산이 취소됩니다.)", tts=False)

		emoji_list : list = ["⭕", "❌"]
		for emoji in emoji_list:
			await distribute_all_finish_warning_message.add_reaction(emoji)

		def reaction_check(reaction, user):
			return (reaction.message.id == distribute_all_finish_warning_message.id) and (user.id == ctx.author.id) and (str(reaction) in emoji_list)

		try:
			reaction, user = await self.bot.wait_for('reaction_add', check = reaction_check, timeout = int(basicSetting[5]))
		except asyncio.TimeoutError:
			for emoji in emoji_list:
				await distribute_all_finish_warning_message.remove_reaction(emoji, self.bot.user)
			return await ctx.send(f"시간이 초과됐습니다. **일괄정산**을 취소합니다!")

		if str(reaction) == "⭕":
			for jungsan_data in jungsan_document:
				result = self.jungsan_db.update_one({"_id":jungsan_data['_id']}, {"$set":{"before_jungsan_ID":[], "after_jungsan_ID":sorted(init_data[jungsan_data['_id']]+jungsan_data['before_jungsan_ID']), "modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])), "itemstatus":"분배완료"}}, upsert = True)
				if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
					await ctx.send(f"{ctx.author.mention}, 일괄정산 실패.") 

			return await ctx.send(f"📥 일괄정산 완료! 📥")
		else:
			return await ctx.send(f"**일괄정산**이 취소되었습니다.\n")

class bankCog(commands.Cog): 
	def __init__(self, bot):
		self.bot = bot	

		self.member_db = self.bot.db.jungsan.member
		self.jungsan_db = self.bot.db.jungsan.jungsandata
		self.guild_db = self.bot.db.jungsan.guild
		self.guild_db_log = self.bot.db.jungsan.guild_log

	################ 수수료 계산기 ################ 
	@commands.command(name=commandSetting[34][0], aliases=commandSetting[34][1:])
	async def tax_check(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[34][0]} [판매금액] (거래소세금)** 양식으로 입력 해주세요\n※ 거래소세금은 미입력시 {basicSetting[7]}%입니다.")
		
		input_money_data : list = args.split()
		len_input_money_data = len(input_money_data)

		try:
			for i in range(len_input_money_data):
				input_money_data[i] = int(input_money_data[i])
		except ValueError:
			return await ctx.send(f"**[판매금액] (거래소세금)**은 숫자로 입력 해주세요.")

		if len_input_money_data < 1 or len_input_money_data > 3:
			return await ctx.send(f"**{commandSetting[34][0]} [판매금액] (거래소세금)** 양식으로 입력 해주세요\n※ 거래소세금은 미입력시 {basicSetting[7]}%입니다.")
		elif len_input_money_data == 2:
			tax = input_money_data[1]
		else:
			tax = basicSetting[7]

		price_first_tax = int(input_money_data[0] * ((100-tax)/100))
		price_second_tax = int(price_first_tax * ((100-tax)/100))
		price_rev_tax = int((input_money_data[0] * 100)/(100-tax)+0.5)

		embed = discord.Embed(
				title = f"🧮  수수료 계산결과 (세율 {tax}% 기준) ",
				description = f"",
				color=0x00ff00
				)
		embed.add_field(name = "⚖️ 수수료 지원", value = f"```등록가 : {price_rev_tax}\n수령가 : {input_money_data[0]}\n세 금 : {price_rev_tax-input_money_data[0]}```")
		embed.add_field(name = "⚖️ 1차 거래", value = f"```등록가 : {input_money_data[0]}\n정산가 : {price_first_tax}\n세 금 : {input_money_data[0]-price_first_tax}```")
		embed.add_field(name = "⚖️ 2차 거래", value = f"```등록가 : {price_first_tax}\n정산가 : {price_second_tax}\n세 금 : {price_first_tax-price_second_tax}```")
		return await ctx.send(embed = embed)

	################ 페이백 계산기 ################ 
	@commands.command(name=commandSetting[35][0], aliases=commandSetting[35][1:])
	async def payback_check(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[35][0]} 거래소가격] [실거래가] (거래소세금)** 양식으로 입력 해주세요\n※ 거래소세금은 미입력시 {basicSetting[7]}%입니다.")
		
		input_money_data : list = args.split()
		len_input_money_data = len(input_money_data)

		try:
			for i in range(len_input_money_data):
				input_money_data[i] = int(input_money_data[i])
		except ValueError:
			return await ctx.send(f"**[판매금액] (거래소세금)**은 숫자로 입력 해주세요.")

		if len_input_money_data < 2 or len_input_money_data > 4:
			return await ctx.send(f"**{commandSetting[35][0]} [거래소가격] [실거래가] (거래소세금)** 양식으로 입력 해주세요\n※ 거래소세금은 미입력시 {basicSetting[7]}%입니다.")
		elif len_input_money_data == 3:
			tax = input_money_data[2]
		else:
			tax = basicSetting[7]

		price_reg_tax = int(input_money_data[0] * ((100-tax)/100))
		price_real_tax = int(input_money_data[1] * ((100-tax)/100))

		reault_payback = price_reg_tax - price_real_tax
		reault_payback1= price_reg_tax - input_money_data[1]

		embed = discord.Embed(
				title = f"🧮  페이백 계산결과1 (세율 {tax}% 기준) ",
				description = f"**```fix\n{reault_payback}```**",
				color=0x00ff00
				)
		embed.add_field(name = "⚖️ 거래소", value = f"```등록가 : {input_money_data[0]}\n정산가 : {price_reg_tax}\n세 금 : {input_money_data[0]-price_reg_tax}```")
		embed.add_field(name = "🕵️ 실거래", value = f"```등록가 : {input_money_data[1]}\n정산가 : {price_real_tax}\n세 금 : {input_money_data[1]-price_real_tax}```")
		await ctx.send(embed = embed)

		embed2 = discord.Embed(
				title = f"🧮  페이백 계산결과2 (세율 {tax}% 기준) ",
				description = f"**```fix\n{reault_payback1}```**",
				color=0x00ff00
				)
		embed2.add_field(name = "⚖️ 거래소", value = f"```등록가 : {input_money_data[0]}\n정산가 : {price_reg_tax}\n세 금 : {input_money_data[0]-price_reg_tax}```")
		embed2.add_field(name = "🕵️ 실거래", value = f"```내판가 : {input_money_data[1]}```")
		return await ctx.send(embed = embed2)

	################ 계좌확인 ################ 
	@commands.command(name=commandSetting[28][0], aliases=commandSetting[28][1:])
	async def account_check(self, ctx):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		embed = discord.Embed(
				title = f"[{member_data['game_ID']}]님 은행 잔고 📝",
				description = f"**```diff\n{member_data['account']}```**",
				color=0x00ff00
				)
		embed.set_thumbnail(url = ctx.author.avatar_url)
		return await ctx.send(embed = embed)

	################ 저축 ################ 
	@commands.command(name=commandSetting[29][0], aliases=commandSetting[29][1:])
	async def bank_save_money(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]):
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[29][0]} [순번] [금액]** 양식으로 입력 해주세요")
		
		input_sell_price_data : list = args.split()
		len_input_sell_price_data = len(input_sell_price_data)

		if len_input_sell_price_data != 2:
			return await ctx.send(f"**{commandSetting[29][0]} [순번] [금액]** 양식으로 입력 해주세요")
		
		try:
			input_sell_price_data[0] = int(input_sell_price_data[0])
			input_sell_price_data[1] = int(input_sell_price_data[1])
		except ValueError:
			return await ctx.send(f"**[순번]** 및 **[금액]**은 숫자로 입력 해주세요")

		if "manager" in member_data['permissions']:
			jungsan_document : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_sell_price_data[0])}, {"itemstatus":"미판매"}]})
		else:
			jungsan_document : dict = self.jungsan_db.find_one({"$and" : [{"$or":[{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_sell_price_data[0])}, {"itemstatus":"미판매"}]})

		if not jungsan_document:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]** 중이 아니거나 없습니다. **[ {commandSetting[13][0]}/{commandSetting[16][0]} ]** 명령을 통해 확인해주세요")
		
		if jungsan_document["gulid_money_insert"]:
			return await ctx.send(f"{ctx.author.mention}님! 해당 정산 내역은 **[ 혈비 ]**로 적립 예정입니다. **[ {commandSetting[24][0]} ]** 명령을 통해 정산해 주세요!")
		
		after_tax_price : int = int(input_sell_price_data[1]*(1-(basicSetting[7]/100)))
		result_each_price : int = int(after_tax_price//len(jungsan_document["before_jungsan_ID"]))

		participant_list : list = jungsan_document["before_jungsan_ID"]

		self.member_db.update_many({"game_ID":{"$in":participant_list}}, {"$inc":{"account":result_each_price}})

		insert_data : dict = {}
		insert_data = {
					"itemstatus":"분배완료",
					"price":after_tax_price,
					"each_price":result_each_price,
					"before_jungsan_ID":[],
					"after_jungsan_ID":sorted(jungsan_document["before_jungsan_ID"]),
					"modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])),
					"bank_money_insert":True
					}

		result = self.jungsan_db.update_one({"_id":input_sell_price_data[0]}, {"$set":insert_data}, upsert = False)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 은행 저축 실패.")		

		return await ctx.send(f"**[ 순번 : {input_sell_price_data[0]} ]**   💰판매금 **[ {after_tax_price} ]**(세율 {basicSetting[7]}% 적용)\n**{jungsan_document['before_jungsan_ID']}**계좌로 인당 **💰 [ {result_each_price} ]** 은행 저축 완료!")

	################ 뽑기저축 ################ 
	@commands.command(name=commandSetting[48][0], aliases=commandSetting[48][1:])
	async def bank_ladder_save_money(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]):
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			return await ctx.send(f"**{commandSetting[48][0]} [순번] [금액] [뽑을인원]** 양식으로 입력 해주세요")
		
		input_sell_price_data : list = args.split()
		len_input_sell_price_data = len(input_sell_price_data)

		if len_input_sell_price_data != 3:
			return await ctx.send(f"**{commandSetting[48][0]} [순번] [금액] [뽑을인원]** 양식으로 입력 해주세요")
		
		try:
			input_sell_price_data[0] = int(input_sell_price_data[0])
			input_sell_price_data[1] = int(input_sell_price_data[1])
			input_sell_price_data[2] = int(input_sell_price_data[2])
		except ValueError:
			return await ctx.send(f"**[순번]**, **[금액]** 및 **[뽑을인원]**은 숫자로 입력 해주세요")

		if "manager" in member_data['permissions']:
			jungsan_document : dict = self.jungsan_db.find_one({"$and" : [{"_id":int(input_sell_price_data[0])}, {"itemstatus":"미판매"}]})
		else:
			jungsan_document : dict = self.jungsan_db.find_one({"$and" : [{"$or":[{"toggle_ID" : str(ctx.author.id)}, {"regist_ID" : str(ctx.author.id)}]}, {"_id":int(input_sell_price_data[0])}, {"itemstatus":"미판매"}]})

		if not jungsan_document:
			return await ctx.send(f"{ctx.author.mention}님! 등록하신 정산 내역이 **[ 미판매 ]** 중이 아니거나 없습니다. **[ {commandSetting[13][0]}/{commandSetting[16][0]} ]** 명령을 통해 확인해주세요")

		if jungsan_document["gulid_money_insert"]:
			return await ctx.send(f"{ctx.author.mention}님! 해당 정산 내역은 **[ 혈비 ]**로 적립 예정입니다. **[ {commandSetting[24][0]} ]** 명령을 통해 정산해 주세요!")
		
		if input_sell_price_data[2] < 1:
			return await ctx.send(f"{ctx.author.mention}님! 추첨인원이 0보다 작거나 같습니다. 재입력 해주세요")
		
		ladder_check : bool = False
		result_ladder = None

		if len(jungsan_document["before_jungsan_ID"]) > input_sell_price_data[2]:
			tmp_before_jungsan_ID : list = []
			tmp_before_jungsan_ID = jungsan_document["before_jungsan_ID"]
			for _ in range(input_sell_price_data[2] + 5):
				random.shuffle(tmp_before_jungsan_ID)
			for _ in range(input_sell_price_data[2] + 5):
				result_ladder = random.sample(tmp_before_jungsan_ID, input_sell_price_data[2])
			await ctx.send(f"**[ {', '.join(sorted(jungsan_document['before_jungsan_ID']))} ]** 중 **[ {', '.join(sorted(result_ladder))} ]** 당첨! 해당 인원의 계좌로 저축합니다.")
			ladder_check = True
		else:
			return await ctx.send(f"{ctx.author.mention}님! 추첨인원이 총 인원과 같거나 많습니다. 재입력 해주세요")
		
		after_tax_price : int = int(input_sell_price_data[1]*(1-(basicSetting[7]/100)))
		result_each_price = int(after_tax_price//input_sell_price_data[2])   

		participant_list : list = sorted(result_ladder)

		self.member_db.update_many({"game_ID":{"$in":participant_list}}, {"$inc":{"account":result_each_price}})

		insert_data : dict = {}
		insert_data = {
					"itemstatus":"분배완료",
					"price":after_tax_price,
					"each_price":result_each_price,
					"before_jungsan_ID":[],
					"after_jungsan_ID":sorted(participant_list),
					"bank_money_insert":True,
					"modifydate":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])),
					"ladder_check":ladder_check
					}

		result = self.jungsan_db.update_one({"_id":input_sell_price_data[0]}, {"$set":insert_data}, upsert = False)
		if result.raw_result["nModified"] < 1 and "upserted" not in result.raw_result:
			return await ctx.send(f"{ctx.author.mention}, 은행 저축 실패.")		

		return await ctx.send(f"**[ 순번 : {input_sell_price_data[0]} ]**   💰판매금 **[ {after_tax_price} ]**(세율 {basicSetting[7]}% 적용)\n**{participant_list}**계좌로 인당 **💰 [ {result_each_price} ]** 은행 저축 완료!")

	################ 입금 #################
	@is_manager() 
	@commands.command(name=commandSetting[30][0], aliases=commandSetting[30][1:])
	async def bank_deposit_money(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")
			
		if not args:
			return await ctx.send(f"**{commandSetting[30][0]} [금액] [아이디] [아이디]...** 양식으로 입력 해주세요")
		
		input_bank_deposit_data : list = args.split()
		len_input_sell_price_data : int = len(input_bank_deposit_data)

		if len_input_sell_price_data < 2:
			return await ctx.send(f"**{commandSetting[30][0]} [금액] [아이디] [아이디]...** 양식으로 입력 해주세요")

		try:
			input_bank_deposit_data[0] = int(input_bank_deposit_data[0])
		except ValueError:
			return await ctx.send(f"**[금액]**은 숫자로 입력 해주세요")

		check_member_data : list = []
		check_member_list : list = []
		wrong_input_id : list = []

		check_member_data = list(self.member_db.find())
		for game_id in check_member_data:
			check_member_list.append(game_id['game_ID'])

		for game_id in input_bank_deposit_data[1:]:
			if game_id not in check_member_list:
				wrong_input_id.append(game_id)

		if len(wrong_input_id) > 0:
			return await ctx.send(f"```입금자 [{', '.join(wrong_input_id)}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")	

		result_update = self.member_db.update_many({"game_ID":{"$in":input_bank_deposit_data[1:]}}, {"$inc":{"account":input_bank_deposit_data[0]}})
		if result_update.modified_count != len(input_bank_deposit_data[1:]):
			return await ctx.send(f"```은행 입금 실패. 정확한 [아이디]를 입력 후 다시 시도 해보세요!```")

		return await ctx.send(f"```ml\n{input_bank_deposit_data[1:]}님 💰[{input_bank_deposit_data[0]}] 은행 입금 완료!.```")

	################ 출금 #################
	@is_manager() 
	@commands.command(name=commandSetting[31][0], aliases=commandSetting[31][1:])
	async def bank_withdraw_money(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")
			
		if not args:
			return await ctx.send(f"**{commandSetting[31][0]} [금액] [아이디] [아이디]...** 양식으로 입력 해주세요")
		
		input_bank_withdraw_data : list = args.split()
		len_input_bank_withdraw_data : int = len(input_bank_withdraw_data)

		if len_input_bank_withdraw_data < 2:
			return await ctx.send(f"**{commandSetting[31][0]} [금액] [아이디] [아이디]...** 양식으로 입력 해주세요")

		try:
			input_bank_withdraw_data[0] = int(input_bank_withdraw_data[0])
		except ValueError:
			return await ctx.send(f"**[금액]**은 숫자로 입력 해주세요")

		check_member_data : list = []
		check_member_list : list = []
		wrong_input_id : list = []

		check_member_data = list(self.member_db.find())
		for game_id in check_member_data:
			check_member_list.append(game_id['game_ID'])

		for game_id in input_bank_withdraw_data[1:]:
			if game_id not in check_member_list:
				wrong_input_id.append(game_id)

		if len(wrong_input_id) > 0:
			return await ctx.send(f"```출금자 [{', '.join(wrong_input_id)}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")	

		result_update = self.member_db.update_many({"game_ID":{"$in":input_bank_withdraw_data[1:]}}, {"$inc":{"account":-input_bank_withdraw_data[0]}})

		if result_update.modified_count != len(input_bank_withdraw_data[1:]):
			return await ctx.send(f"```은행 출금 실패. 정확한 [아이디]를 입력 후 다시 시도 해보세요!```")

		return await ctx.send(f"```ml\n{input_bank_withdraw_data[1:]}님 💰[{input_bank_withdraw_data[0]}] 은행 출금 완료!.```")

	################ 혈비입금 #################
	@is_manager() 
	@commands.command(name=commandSetting[32][0], aliases=commandSetting[32][1:])
	async def guild_support_money_save(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")
			
		if not args:
			return await ctx.send(f"**{commandSetting[32][0]} [금액] (*사유)** 양식으로 입력 해주세요")

		reason : str = ""

		if args.find("*") != -1:
			reason = args[args.find("*")+1:]
			args = args[:args.find("*")]

		try:
			args = int(args)
		except ValueError:
			return await ctx.send(f"**[금액]**은 숫자로 입력 해주세요")

		result_guild_update : dict = self.guild_db.update_one({"_id":"guild"}, {"$inc":{"guild_money":args}}, upsert = True)
		if result_guild_update.raw_result["nModified"] < 1 and "upserted" not in result_guild_update.raw_result:
			return await ctx.send(f"```혈비 입금 실패!```")
		insert_log_data = {
					"in_out_check":True,  # True : 입금, False : 출금
					"log_date":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])),
					"money":args,
					"member_list":[],
					"reason":reason
		}
		result_guild_log = self.guild_db_log.insert_one(insert_log_data)

		total_guild_money : dict = self.guild_db.find_one({"_id":"guild"})

		embed = discord.Embed(
				title = f"💰  혈비 입금 완료",
				description = f"",
				color=0x00ff00
				)
		embed.add_field(name = f"**입금**", value = f"**```fix\n{args}```**")
		embed.add_field(name = f"**혈비**", value = f"**```fix\n{total_guild_money['guild_money']}```**")
		if reason != "":
			embed.add_field(name = f"**사유**", value = f"**```fix\n{reason}```**", inline=False)
		return await ctx.send(embed = embed)

	################ 혈비출금 #################
	@is_manager() 
	@commands.command(name=commandSetting[49][0], aliases=commandSetting[49][1:])
	async def guild_support_money_withdraw(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")
			
		if not args:
			return await ctx.send(f"**{commandSetting[49][0]} [금액]** 양식으로 입력 해주세요")

		guild_support_money_withdraw_data : list = args.split(" *")
		if len(guild_support_money_withdraw_data) != 2:
			return await ctx.send(f"**{commandSetting[49][0]} [금액] *[사유]** 양식으로 입력 해주세요")

		try:
			guild_support_money_withdraw_data[0] = int(guild_support_money_withdraw_data[0])
		except ValueError:
			return await ctx.send(f"**[금액]**은 숫자로 입력 해주세요")

		result_guild_update : dict = self.guild_db.update_one({"_id":"guild"}, {"$inc":{"guild_money":-guild_support_money_withdraw_data[0]}}, upsert = True)
		if result_guild_update.raw_result["nModified"] < 1 and "upserted" not in result_guild_update.raw_result:
			return await ctx.send(f"```혈비 출금 실패!```")
		insert_log_data = {
					"in_out_check":False,  # True : 입금, False : 출금
					"log_date":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])),
					"money":guild_support_money_withdraw_data[0],
					"member_list":[],
					"reason":guild_support_money_withdraw_data[1]
		}
		result_guild_log = self.guild_db_log.insert_one(insert_log_data)

		total_guild_money : dict = self.guild_db.find_one({"_id":"guild"})

		embed = discord.Embed(
				title = f"💰  혈비 출금 완료",
				description = f"",
				color=0x00ff00
				)
		embed.add_field(name = f"**출금**", value = f"**```fix\n{guild_support_money_withdraw_data[0]}```**")
		embed.add_field(name = f"**혈비**", value = f"**```fix\n{total_guild_money['guild_money']}```**")
		return await ctx.send(embed = embed)

	################ 혈비지원 #################
	@is_manager() 
	@commands.command(name=commandSetting[33][0], aliases=commandSetting[33][1:])
	async def guild_support_money(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		guild_data : dict = self.guild_db.find_one({"_id":"guild"})

		if not guild_data:
			return await ctx.send(f"등록된 혈비가 없습니다!")
			
		if not args:
			return await ctx.send(f"**{commandSetting[33][0]} [금액] [아이디1] [아이디2] ... *[사유]** 양식으로 입력 해주세요")
		
		input_guild_support_money_data : list = args.split(" *")
		if len(input_guild_support_money_data) != 2:
			return await ctx.send(f"**{commandSetting[33][0]} [금액] [아이디] [아이디2] ... *[사유]** 양식으로 입력 해주세요")

		input_guild_support_money_ID_data : list = input_guild_support_money_data[0].split(" ")

		input_guild_support_money_ID_data = [input_guild_support_money_ID_data[0]] + list(set(input_guild_support_money_ID_data[1:]))

		try:
			input_guild_support_money_ID_data[0] = int(input_guild_support_money_ID_data[0])
		except ValueError:
			return await ctx.send(f"**[금액]**은 숫자로 입력 해주세요")

		check_member_data : list = []
		check_member_list : list = []
		wrong_input_id : list = []

		check_member_data = list(self.member_db.find())
		for game_id in check_member_data:
			check_member_list.append(game_id['game_ID'])

		for game_id in input_guild_support_money_ID_data[1:]:
			if game_id not in check_member_list:
				wrong_input_id.append(game_id)

		if len(wrong_input_id) > 0:
			return await ctx.send(f"```지원자 [{', '.join(wrong_input_id)}](은)는 혈원으로 등록되지 않은 아이디 입니다.```")	

		result_update = self.member_db.update_many({"game_ID":{"$in":input_guild_support_money_ID_data[1:]}}, {"$inc":{"account":input_guild_support_money_ID_data[0]}})

		if result_update.modified_count != len(input_guild_support_money_ID_data[1:]):
			return await ctx.send(f"```혈비 지원 실패. 정확한 [아이디]를 입력 후 다시 시도 해보세요!```")
		insert_log_data = {
					"in_out_check":False, # True : 입금, False : 출금
					"log_date":datetime.datetime.now() + datetime.timedelta(hours = int(basicSetting[8])),
					"money":str(input_guild_support_money_ID_data[0]*len(input_guild_support_money_ID_data[1:])),
					"member_list":input_guild_support_money_ID_data[1:],
					"reason":input_guild_support_money_data[1]
		}
		result_guild_log = self.guild_db_log.insert_one(insert_log_data)

		total_support_money : int = len(input_guild_support_money_ID_data[1:]) * input_guild_support_money_ID_data[0]

		result_guild_update = self.guild_db.update_one({"_id":"guild"}, {"$inc":{"guild_money":-total_support_money}}, upsert = False)
		if result_guild_update.raw_result["nModified"] < 1 and "upserted" not in result_guild_update.raw_result:
			return await ctx.send(f"```혈비 지원 실패!```")

		embed = discord.Embed(
				title = f"🤑 혈비 지원 완료",
				description = f"```css\n[{input_guild_support_money_data[1]}] 사유로 💰[{input_guild_support_money_ID_data[0]}]씩 혈비에서 지원했습니다.```",
				color=0x00ff00
				)
		embed.add_field(name = f"**👥  명단**", value = f"**```fix\n{', '.join(input_guild_support_money_ID_data[1:])}```**")
		embed.add_field(name = f"**💰  인당지원금**", value = f"**```fix\n{input_guild_support_money_ID_data[0]}```**")
		embed.add_field(name = f"**💰  토탈지원금**", value = f"**```fix\n{int(input_guild_support_money_ID_data[0])*len(input_guild_support_money_ID_data[1:])}```**")
		return await ctx.send(embed = embed)

	################ 창고검색 #################
	@commands.command(name=commandSetting[44][0], aliases=commandSetting[44][1:])
	async def guild_inventory_search(self, ctx, *, args : str = None):
		if ctx.message.channel.id != int(basicSetting[6]) or basicSetting[6] == "":
			return

		member_data : dict = self.member_db.find_one({"_id":ctx.author.id})

		if not member_data:
			return await ctx.send(f"{ctx.author.mention}님은 혈원으로 등록되어 있지 않습니다!")

		if not args:
			pipeline = [
						{"$match": {"itemstatus":"미판매"}},  # 조건
						{"$group": {"_id": "$item", "count": {"$sum":1}}}  # 요런식으로 변환해준다.
					]

			item_counts = self.jungsan_db.aggregate(pipeline)

			sorted_item_counts : dict = sorted(item_counts, key=lambda item_counts:item_counts['count'], reverse = True)
			len_sorted_item_counts = len(sorted_item_counts)
			#print(sorted_item_counts)

			embed_list : list = []
			embed_index : int = 0
			embed_cnt : int = 0

			embed = discord.Embed(title = f'📦  `창고 내역`', description = "", color = 0x00ff00)

			embed_list.append(embed)

			if len_sorted_item_counts > 0 :
				for item_data in sorted_item_counts:
					embed_cnt += 1
					if embed_cnt > 24 :
						embed_cnt = 0
						embed_index += 1
						tmp_embed = discord.Embed(
							title = "",
							description = "",
							color=0x00ff00
							)
						embed_list.append(tmp_embed)
					embed_list[embed_index].add_field(name = item_data['_id'], value = f"```{item_data['count']}```")
				embed.set_footer(text = f"전체 아이템 종류  :  {len_sorted_item_counts}개")
				if len(embed_list) > 1:
					for embed_data in embed_list:
						await asyncio.sleep(0.1)
						await ctx.send(embed = embed_data)
					return
				else:
					return await ctx.send(embed=embed, tts=False)
			else :
				embed.add_field(name = '\u200b\n', value = '창고가 비었습니다.\n\u200b')
				return await ctx.send(embed=embed, tts=False)
		else:
			toggle_documents = list(self.jungsan_db.find({"itemstatus" : "미판매", "item" : args}))

			if len(toggle_documents) == 0:
				return await ctx.send(f"`창고`에 해당 아이템(`{args}`)이 없습니다!")

			toggle_list : list = []
			tmp_toggle_list : list = []

			for toggle in toggle_documents:
				tmp_toggle_list.append(toggle["toggle"])
			
			toggle_name_list = list(set(tmp_toggle_list))

			for name in toggle_name_list:
				toggle_list.append(f"{name}({tmp_toggle_list.count(name)}개)")

			embed = discord.Embed(title = f'📦  `{args}` 소지자 (총 `{len(toggle_name_list)}`명)', description = "", color = 0x00ff00)	
			embed.description = f"```{', '.join(toggle_list)}```"

			return await ctx.send(embed = embed)

ilsang_distribution_bot : IlsangDistributionBot = IlsangDistributionBot()
ilsang_distribution_bot.add_cog(settingCog(ilsang_distribution_bot))
ilsang_distribution_bot.add_cog(adminCog(ilsang_distribution_bot))
ilsang_distribution_bot.add_cog(memberCog(ilsang_distribution_bot))
ilsang_distribution_bot.add_cog(manageCog(ilsang_distribution_bot))
ilsang_distribution_bot.add_cog(bankCog(ilsang_distribution_bot))
ilsang_distribution_bot.run()