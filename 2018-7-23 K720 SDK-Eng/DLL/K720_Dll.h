#ifndef	__K720_DLL_H
#define	__K720_DLL_H

///////////////////预定义公共错误///////////////////////////
#define	Bad_CommOpen			-101//串口未打开
#define	Bad_CommSet				-102//串口设置错误

#define	Bad_CommTimeouts			-999//串口读写超时设置错误
#define	Bad_CommQueue				-998//串口缓冲区操作错误

///////////////////串口的读写的错误/////////////////////////
#define	Bad_CommRead				-103//串口读超时
#define	Bad_CommWrite				-104//串口写超时
#define	ACK_Timeout				-105//串口ACK标识超时
#define	EOT_Timeout				-106//串口Eot标识超时
#define	PACKET_Timeout				-107//最后一包数据超时
#define	WRONG_PacketHead			-108//错误的包头 
#define	WRONG_PacketLen				-109//错误的包的长度
#define WRONG_BCC				-110//BBC校验错误
#define Bad_Parameter				-201//传入函数的参数错误
#define	Bad_CommClose				-202//关闭串口错误
#define WRONG_ADDRESS			-203//错误地址


/////////////////RF610串口操作/////////////////////////////////////
HANDLE __stdcall K720_CommOpen(char *Port);
HANDLE __stdcall K720_CommOpenWithBaud(char *Port, unsigned int _data);
int __stdcall K720_CommClose(HANDLE ComHandle);
int __stdcall K720_GetSysVersion(HANDLE ComHandle, char *strVersion);

///////////////////////////波特率操作函数///////////////////////////////////
//int __stdcall K720_SetCommBaud(HANDLE ComHandle, unsigned int _Baud, char *RecordInfo);
//int __stdcall K720_Reset(HANDLE ComHandle, char *RecordInfo);
//int __stdcall K720_GetHardVersion(HANDLE ComHandle, BYTE *_VerCode, char *RecordInfo);


/////////////////RF610 S50卡片操作函数////////////////////////////
int __stdcall K720_S50DetectCard(HANDLE ComHandle, BYTE MacAddr, char *RecordInfo);
int __stdcall K720_S50GetCardID(HANDLE ComHandle, BYTE MacAddr, BYTE *_CardID, char *RecordInfo);
int __stdcall K720_S50LoadSecKey(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE _KEYType, BYTE *_KEY, char *RecordInfo);
int __stdcall K720_S50ReadBlock(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE BlockAddr, BYTE *_BlockData, char *RecordInfo);
int __stdcall K720_S50WriteBlock(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE BlockAddr,BYTE *_BlockData, char *RecordInfo);
int __stdcall K720_S50InitValue(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE BlockAddr, BYTE *_Data, char *RecordInfo);
int __stdcall K720_S50Increment(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE BlockAddr, BYTE *_Data, char *RecordInfo);
int __stdcall K720_S50Decrement(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE BlockAddr, BYTE *_Data, char *RecordInfo);
int __stdcall K720_S50Halt(HANDLE ComHandle, BYTE MacAddr, char *RecordInfo);


//////////////////////////////RF610 S70卡片操作函数////////////////////////////
int __stdcall K720_S70DetectCard(HANDLE ComHandle, BYTE MacAddr, char *RecordInfo);
int __stdcall K720_S70GetCardID(HANDLE ComHandle, BYTE MacAddr, BYTE *_CardID, char *RecordInfo);
int __stdcall K720_S70LoadSecKey(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE _KEYType, BYTE *_KEY, char *RecordInfo);
int __stdcall K720_S70ReadBlock(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE BlockAddr, BYTE *_BlockData, char *RecordInfo);
int __stdcall K720_S70WriteBlock(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE BlockAddr, BYTE *_BlockData, char *RecordInfo);
int __stdcall K720_S70InitValue(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE BlockAddr, BYTE *_Data, char *RecordInfo);
int __stdcall K720_S70Increment(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE BlockAddr, BYTE *_Data, char *RecordInfo);
int __stdcall K720_S70Decrement(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE BlockAddr, BYTE *_Data, char *RecordInfo);
int __stdcall K720_S70Halt(HANDLE ComHandle, BYTE MacAddr, char *RecordInfo);


//////////////////////////////RF610 UL卡片操作函数////////////////////////////
int __stdcall K720_ULDetectCard(HANDLE ComHandle, BYTE MacAddr, char *RecordInfo);
int __stdcall K720_ULGetCardID(HANDLE ComHandle, BYTE MacAddr, BYTE *_CardID, char *RecordInfo);
int __stdcall K720_ULReadBlock(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE *_BlockData, char *RecordInfo);
int __stdcall K720_ULWriteBlock(HANDLE ComHandle, BYTE MacAddr, BYTE SectorAddr, BYTE *_BlockData, char *RecordInfo);
int __stdcall K720_ULHalt(HANDLE ComHandle, BYTE MacAddr, char *RecordInfo);

/////////////////////////////CPU卡操作函数/////////////////////////////////////
int __stdcall K720_CPUCardPowerOn(HANDLE ComHandle, BYTE MacAddr, BYTE *szATR, char *RecordInfo);
int __stdcall K720_CPUAPDU(HANDLE ComHandle, BYTE MacAddr, BYTE SCH, int _dataLen, BYTE _APDUData[], BYTE* RCH,BYTE _exData[], int *_exdataLen, char *RecordInfo);



/**********************************D1801操作函数***************************************************/
int __stdcall K720_GetVersion(HANDLE ComHandle, BYTE MacAddr, BYTE Version[20], char *RecordInfo);
int __stdcall K720_SendCmd(HANDLE ComHandle, unsigned char MacAddr, char *p_Cmd, int CmdLen, char *RecordInfo);
int __stdcall K720_Query(HANDLE ComHandle, BYTE MacAddr, BYTE StateInfo[3], char *RecordInfo);
int __stdcall K720_SensorQuery(HANDLE ComHandle, BYTE MacAddr, BYTE StateInfo[4], char *RecordInfo);
int __stdcall K720_GetCountSum(HANDLE ComHandle, BYTE MacAddr, BYTE StateInfo[11], char *RecordInfo);
int __stdcall K720_ClearSendCount(HANDLE ComHandle, BYTE MacAddr, char *RecordInfo);
int __stdcall K720_ClearRecycleCount(HANDLE ComHandle, BYTE MacAddr, char *RecordInfo);
int __stdcall K720_AutoTestMac(HANDLE ComHandle, unsigned char MacAddr, char *RecordInfo);


/**********************************15693操作函数***************************************************/
int __stdcall K720_15693LockDSFID(HANDLE ComHandle,BYTE MacAddr,bool bUid,BYTE Uid[8], char *RecordInfo);
int __stdcall K720_15693LockAFI(HANDLE ComHandle,BYTE MacAddr,bool bUid,BYTE Uid[8], char *RecordInfo);
int __stdcall K720_15693LockBlock(HANDLE ComHandle,BYTE MacAddr,bool bUid,BYTE Uid[8],BYTE LockAddress, char *RecordInfo);
int __stdcall K720_15693WriteAFI(HANDLE ComHandle,BYTE MacAddr,bool bUid,BYTE Uid[8],BYTE WriteBit, char *RecordInfo);
int __stdcall K720_15693WriteDSFID(HANDLE ComHandle,BYTE MacAddr,bool bUid,BYTE Uid[8],BYTE WriteBit, char *RecordInfo);
int __stdcall K720_15693ReadSafeBit(HANDLE ComHandle, BYTE MacAddr,bool bUid,BYTE Uid[8],BYTE BlockAddr, BYTE BlockLen,BYTE* ReadBlockLen,BYTE BlockLockStatus[], char *RecordInfo);
int __stdcall K720_15693GetMessage(HANDLE ComHandle, BYTE MacAddr,bool bUid,BYTE Uid[8],BYTE Message[15], char *RecordInfo);
int __stdcall K720_15693ChooseCard(HANDLE ComHandle,BYTE MacAddr,bool bUid,BYTE Uid[8], char *RecordInfo);
int __stdcall K720_15693WriteData(HANDLE ComHandle, BYTE MacAddr,bool bUid,BYTE Uid[8],BYTE BlockAddr, BYTE BlockLen, BYTE _BlockData[],BYTE *WriteBlockLen, char *RecordInfo);
int __stdcall K720_15693ReadData(HANDLE ComHandle, BYTE MacAddr,bool bUid,BYTE Uid[8],BYTE BlockAddr, BYTE BlockLen, BYTE _BlockData[],BYTE* ReadBlockLen, char *RecordInfo);
int __stdcall K720_15693GetUid(HANDLE ComHandle, BYTE MacAddr, BYTE UID[8], char *RecordInfo);

#endif