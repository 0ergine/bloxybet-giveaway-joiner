import json
import httpx
import disnake
import websockets

async def send_json_request(ws, request):
    await ws.send(json.dumps(request))
    
async def receive_json_request(ws):
    response = await ws.recv()
    if response:
        return json.loads(response)


configJson = json.load(open("config.json", "r"))
session = httpx.AsyncClient(headers={"authorization": configJson["bloxybet"]})

from disnake.ext import commands
class Discord(commands.InteractionBot):
    async def on_ready(self):
        output = self.get_channel(configJson["logs"])
        while True:
            try:
                async for websocket in websockets.connect("wss://bloxyapi.com/api/giveaway_ws"):
                    print("Connected"); await output.send("Connected")
                    while True:
                        try:
                            await send_json_request(websocket, {"action": "heartbeat"})
                            
                            response = (await receive_json_request(websocket))
                            if (response["action"] == "created"): 
                                print(f"Giveaway Started ({response['_id']})")
                                joinReq = await session.post("https://bloxyapi.com/api/join_giveaway", json={"giveaway_id": response["_id"]})
                                        
                                giveawayEmbed = disnake.Embed(title=f"Giveaway Started (<t:{int(response['ends'])}:R>)", description=joinReq.text, url="https://bloxybet.com/")
                                giveawayEmbed.add_field(name="Item", value=response["item"]["game_name"])
                                giveawayEmbed.add_field(name="Value", value=response["item"]["value"])
                                giveawayEmbed.set_thumbnail(url=response["item"]["thumbnail"])
                                giveawayEmbed.set_footer(text=response["_id"])
                                await output.send(embed=giveawayEmbed)

                            elif (response["action"] == "ended"):
                                print(f"Giveaway Ended ({response['_id']})")
                                giveawayEmbed = disnake.Embed(title="Giveaway Ended", description=str(response["winner"]), url="https://bloxybet.com/")
                                giveawayEmbed.add_field(name="Item", value=response["item"]["game_name"])
                                giveawayEmbed.add_field(name="Value", value=response["item"]["value"])
                                giveawayEmbed.set_thumbnail(url=response["item"]["thumbnail"])
                                giveawayEmbed.set_footer(text=f"{ str(((1 / response['participants']) * 100))[:4]}% {response['_id']}")
                                await output.send(embed=giveawayEmbed)

                            elif (not response["action"] == "update"):
                                print("No active giveaways")

                        except Exception as err:
                            await output.send(err); break
            except:
                await output.send("cant even connect to websocket")
    
    @commands.slash_command(description="shows your current inventory")
    async def balance(message):
        inventoryReq = await session.get("https://bloxyapi.com/api/inventory")     
        balanceEmbed = disnake.Embed(title='Empty', description='')  
        try:
            inventoryJson = inventoryReq.json()
            if len(inventoryJson["inventory"]) > 0:
                balanceEmbed.description += "`"
                for item in inventoryJson["inventory"]:
                    balanceEmbed.description += f'{item["game_name"]} (${item["value"]})\n'
                balanceEmbed.description += "`"
                balanceEmbed.title = f'Inventory (total {sum( [item["value"] for item in inventoryJson["inventory"]] )})'
        except:
            pass
        await message.response.send_message(embed=balanceEmbed) 

client = Discord()
client.add_slash_command(client.balance)
client.run(configJson["discord"])





