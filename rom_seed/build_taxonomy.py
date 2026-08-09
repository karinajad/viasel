# Build the confirmed canonical taxonomy: Exhibits Legend + confirmed Section A/B additions,
# physics-only (location/vendor stripped), with natural denominators.
import zipfile,re,csv
from xml.etree import ElementTree as ET
NS='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
RN='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PK='{http://schemas.openxmlformats.org/package/2006/relationships}'
def ci(r):
    m=re.match(r'([A-Z]+)\d+',r); c=0
    for ch in (m.group(1) if m else ''): c=c*26+(ord(ch)-64)
    return c-1
def sh(z):
    try:r=ET.fromstring(z.read('xl/sharedStrings.xml'))
    except:return[]
    return[''.join(t.text or '' for t in si.iter(f'{NS}t'))for si in r.findall(f'{NS}si')]
def shs(z):
    wb=ET.fromstring(z.read('xl/workbook.xml'));rl=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    tg={x.get('Id'):x.get('Target')for x in rl.findall(f'{PK}Relationship')};o=[]
    for s in wb.find(f'{NS}sheets').findall(f'{NS}sheet'):
        t=tg.get(s.get(f'{RN}id'),'');t='xl/'+t.lstrip('/')if t and not t.startswith('xl/')else t
        o.append((s.get('name'),t))
    return o
def rws(z,t,s):
    root=ET.fromstring(z.read(t));sd=root.find(f'{NS}sheetData');o=[]
    for row in sd.findall(f'{NS}row'):
        d={}
        for c in row.findall(f'{NS}c'):
            i=ci(c.get('r')or'A1');ty=c.get('t');v=c.find(f'{NS}v');ins=c.find(f'{NS}is')
            d[i]=(s[int(v.text)]if ty=='s'and v is not None else(''.join(x.text or''for x in ins.iter(f'{NS}t'))if ins is not None else(v.text if v is not None else'')) or'').strip()
        o.append(d)
    return o
def den(s):
    for p,d in[(r'\d+(?:\.\d+)?\s*[- ]?tons?','$/ton'),(r'\d+(?:\.\d+)?\s*MVA','$/MVA'),(r'\d+(?:\.\d+)?\s*kVA','$/kVA'),(r'\d+(?:\.\d+)?\s*MW','$/MW'),(r'\d+(?:\.\d+)?\s*kW','$/kW'),(r'\d+\s*A\b|amp','$/A'),(r'\d+\s*ft','$/ft')]:
        if re.search(p,s or'',re.I):return d
    return'$/unit'
out=[]
z=zipfile.ZipFile('/Users/karinaadum/Documents/viasel/ofci data/Exhibits.xlsx');s=sh(z)
for n,t in shs(z):
    if n!='Legend':continue
    on=False
    for r in rws(z,t,s):
        if r.get(0,'')=='Design Term'and r.get(1,'')=='Unit Type Code':on=True;continue
        if on and r.get(1,''):
            code=r.get(1,'');subs=[r.get(i,'')for i in range(2,12)if r.get(i,'')]
            if subs:
                for su in subs: out.append((r.get(0,''),code,su,den(su),'exhibits-legend'))
            else: out.append((r.get(0,''),code,'',den(code),'exhibits-legend'))
z.close()
# Section A additions (physics-only, location/vendor stripped)
A=[('CHLR','Air-Cooled Chiller','500 Ton','$/ton'),('CHLR','Air-Cooled Chiller','850 Ton','$/ton'),
('GEN','Generator','500kW','$/kW'),('H GEN','House Generator','500kW','$/kW'),
('XFMR','Padmount Transformer','3200kVA','$/kVA'),('XFMR','House Transformer','500kVA','$/kVA'),
('UPS','UPS','200kW','$/kW'),('UPS','UPS','2000kW','$/kW'),
('CRAH','CRAH','112kW','$/kW'),('CRAH','CRAH','211kW','$/kW'),('CRAH','Fan Wall','700kW','$/kW'),
('CRAC','Computer Room Air Conditioner','230kW Dx','$/kW'),('PDU','PDU','75kVA','$/kVA'),
('PDU','Busway','40ft 400A','$/ft'),('PDU','Busway','50ft 400A','$/ft'),('PDU','Busway','96ft 3000A','$/ft'),
('CRAH','HAC','50ft Brooklyn Lite','$/ft'),('SWGR','MV Switchgear','2500A Metalclad','$/unit'),
('SWBD','LV Switchboard','3200A 415V','$/A'),('TST','Thermal Pump Skid','8in 3000gal TES','$/unit')]
for d,c,su,dn in A: out.append((d,c,su,dn,'candidate-A-new-subtype'))
# Section B new HV types (location-agnostic)
B=[('PXFMR','Power Transformer','360MVA 345-34.5kV','$/MVA'),('HVSWGR','HV Distribution Switchgear','34.5/38kV','$/unit'),
('CB','Circuit Breaker','345kV','$/unit'),('DSW','Disconnect Switch','345kV','$/unit'),('SA','Surge Arrestor','345kV','$/unit'),
('CVT','Coupling Voltage Transformer','345kV','$/unit'),('CAP','Capacitor Bank','34.5kV','$/unit'),
('CLR','Current Limiting Reactor','34.5kV','$/unit'),('SST','Station Service Transformer','','$/kVA'),
('CMBX','Combined Transformer','','$/MVA'),('NGE','Neutral Grounding Equipment','34.5kV','$/unit'),
('SGENC','Switchgear Enclosure','','$/unit'),('CTLH','Control House','','$/unit')]
for d,c,su,dn in B: out.append((d,c,su,dn,'candidate-B-new-type'))
with open('equipment_types_canonical.csv','w',newline='')as f:
    w=csv.writer(f);w.writerow(['design_term','unit_type_code','sub_type','natural_denominator','source']);w.writerows(out)
print(f"equipment_types_canonical.csv written: {len(out)} rows")
print(f"  from Exhibits Legend: {sum(1 for r in out if r[4]=='exhibits-legend')}")
print(f"  candidate new sub-types (A): {sum(1 for r in out if r[4]=='candidate-A-new-subtype')}")
print(f"  candidate new HV types  (B): {sum(1 for r in out if r[4]=='candidate-B-new-type')}")
import collections
print("  denominators used:",dict(collections.Counter(r[3] for r in out)))
