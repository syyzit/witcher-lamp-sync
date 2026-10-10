// Reports Geralt's equipped sign to dx12user.settings so an external
// process can drive a lamp. The game enum is not the hotkey order:
//   0 Aard, 1 Yrden, 2 Igni, 3 Quen, 4 Axii, 5 None.

@addField(W3PlayerWitcher) var LS_last : int;
@addField(W3PlayerWitcher) var LS_ready : bool;

function LS_WriteSign(player : W3PlayerWitcher)
{
	var sign : ESignType;
	var signId : int;
	var cfg : CInGameConfigWrapper;

	if (!player)
		return;

	cfg = (CInGameConfigWrapper)theGame.GetInGameConfigWrapper();
	if (!cfg)
		return;

	sign = player.GetEquippedSign();
	signId = (int)sign;
	if (player.LS_ready && signId == player.LS_last)
		return;

	cfg.SetVarValue('LampSync', 'Sign', "" + signId);
	theGame.SaveUserSettings();
	player.LS_last = signId;
	player.LS_ready = true;
}

@wrapMethod(W3PlayerWitcher) function OnSpawned(spawnData : SEntitySpawnData)
{
	wrappedMethod(spawnData);
	AddTimer('LS_Tick', 0.25, true);
	LS_WriteSign(GetWitcherPlayer());
}

@addMethod(W3PlayerWitcher) timer function LS_Tick(dt : float, id : int)
{
	LS_WriteSign(GetWitcherPlayer());
}

@wrapMethod(W3PlayerWitcher) function SetEquippedSign(signType : ESignType)
{
	wrappedMethod(signType);
	LS_WriteSign(GetWitcherPlayer());
}
