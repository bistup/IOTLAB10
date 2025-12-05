from uprotobuf import *


@registerMessage
class TimeMessage(Message):
    _proto_fields=[
        dict(name='hour', type=WireType.Varint, subType=VarintSubType.UInt32, fieldType=FieldType.Required, id=1),
        dict(name='minute', type=WireType.Varint, subType=VarintSubType.UInt32, fieldType=FieldType.Required, id=2),
        dict(name='second', type=WireType.Varint, subType=VarintSubType.UInt32, fieldType=FieldType.Required, id=3),
    ]

@registerMessage
class TemperaturereadingMessage(Message):
    _proto_fields=[
        dict(name='publisher_id', type=WireType.Length, subType=LengthSubType.String, fieldType=FieldType.Required, id=1),
        dict(name='temperature', type=WireType.Bit64, subType=FixedSubType.Double, fieldType=FieldType.Required, id=2),
        dict(name='time', type=WireType.Varint, subType=VarintSubType.UInt64, fieldType=FieldType.Required, id=3),
    ]
