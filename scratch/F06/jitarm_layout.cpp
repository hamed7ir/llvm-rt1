// F0.6 — headerless replication of every bitfield-bearing record in js/src/jit/arm,
// verbatim member sequences, to MEASURE MS-ABI vs Itanium-ABI sizeof divergence.
// Sources (current Varan tree):
//   uxp/js/src/jit/arm/Assembler-arm.h  :446-456, 485-487, 511-518, 544-546,
//                                        589-591, 603, 619-641, 688-689,
//                                        1131-1134, 1168-1170
//   uxp/js/src/jit/arm/Assembler-arm.cpp:3140-3145 (PoolHintData), 5245-5247 (PoolHeader::Header)
//   uxp/js/src/jit/arm/Architecture-arm.h:363-376 (VFPRegister), 425-426 (VFPRegIndexSplit)
typedef unsigned int      u32;
typedef int               i32;
typedef unsigned char     u8;

// ---- CONTROLS ------------------------------------------------------------
// MUST-BE-FOUND (positive): the pre-fix PoolHeader shape. MS 12 / Itanium 4.
struct C_PosPreFix { u32 size:15; bool isNatural:1; u32 ONES:16; };
// MUST-NOT-BE-FOUND (negative): a plain 4-byte-only bitfield struct. 4 on both.
struct C_NegAllU32 { u32 a:15; u32 b:1; u32 c:16; };
// Reporting sanity controls (must be 1 and 20).
struct C_One   { u8 a; };
struct C_Twenty{ u32 a,b,c,d; u8 e; };

// ---- Architecture-arm.h -------------------------------------------------
enum RegType : u32 { Single=0, Double=1, UInt=2, Int=3 };
struct A_VFPRegister { RegType kind:2; u32 code_:5; u32 _isInvalid:1; u32 _isMissing:1; };
struct A_VFPRegIndexSplit { const u32 block:4; const u32 bit:1; };

// ---- Assembler-arm.h ----------------------------------------------------
struct B_Op2Reg   { u32 rm_:4; u32 rrs_:1; u32 type_:2; u32 shiftAmount_:5; u32 pad_:20; };
struct B_Imm8mData{ u32 ctrl_:12; u32 buff_:19; u32 invalid_:1; };
struct B_Imm8Data { u32 data_:8; u32 rot_:4; u32 buff_:19; u32 invalid_:1; };
struct B_Imm8VFPO { u32 imm4L_:4; u32 pad_:4; u32 imm4H_:4; };
struct B_Imm8VFPI { u32 imm4L:4; u32 imm4H:4; i32 isInvalid:24; };
struct B_Imm12Dat { u32 data_:12; };
struct B_Reg      { u32 shiftAmount_:5; u32 mustZero_:1; u32 rs_:4; };
struct B_Other    { u32 oper_:31; u32 invalid_:1; };
struct B_Imm16Dat { u32 lower_:12; u32 pad_:4; u32 upper_:4; u32 invalid_:12; };
// >>> THE CANDIDATE: Assembler-arm.h:1160-1170, `enum class Tag : uint8_t` <<<
enum class OperandTag : u8 { OP2, MEM, FOP };
struct B_Operand  { OperandTag tag_:8; u32 reg_:5; i32 offset_; };
// counterfactual: the same class with a 4-byte-underlying Tag
enum class OperandTag32 : u32 { OP2, MEM, FOP };
struct B_OperandU32 { OperandTag32 tag_:8; u32 reg_:5; i32 offset_; };

// ---- Assembler-arm.cpp --------------------------------------------------
enum LoadType : u32 { PoolBOGUS=0, PoolDTR=1, PoolBranch=2, PoolVDTR=3 };
struct C_PoolHintData { u32 index_:16; u32 cond_:4; LoadType loadType_:2; u32 destReg_:5; u32 destType_:1; u32 ONES:4; };
struct C_PoolHeader   { u32 size:15; u32 isNatural:1; u32 ONES:16; };

// Force layout of everything (belt-and-braces; -fdump-record-layouts-complete also does it).
C_PosPreFix g1; C_NegAllU32 g2; C_One g3; C_Twenty g4;
A_VFPRegister g5; A_VFPRegIndexSplit g6 = {0,0};
B_Op2Reg g7; B_Imm8mData g8; B_Imm8Data g9; B_Imm8VFPO g10; B_Imm8VFPI g11;
B_Imm12Dat g12; B_Reg g13; B_Other g14; B_Imm16Dat g15; B_Operand g16; B_OperandU32 g17;
C_PoolHintData g18; C_PoolHeader g19;
