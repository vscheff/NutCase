"""Page-space layout using native projected extents; all coordinates in millimeters."""
SHEETS = {"ANSI-B": (431.8, 279.4), "ANSI-C": (558.8, 431.8), "ANSI-D": (863.6, 558.8), "ANSI-A": (279.4, 215.9), "A3": (420.0, 297.0), "A4": (297.0, 210.0)}
PREFERRED_SCALES = (20, 10, 5, 4, 3, 2.5, 2, 1, 0.5, 0.25, 0.2, 0.1, 0.05, 0.02, 0.01)


def select_layout(envelopes, sheet="ANSI-B", dimensions=False):
    width, height = SHEETS[sheet]
    content = {"left": 22.0, "right": width - 22.0, "top": 24.0, "bottom": height - 65.0}
    gap, row_gap, label_space = 24.0, 18.0, 20.0 if dimensions else 11.0
    top_lane = 18.0 if dimensions else 0.0
    padding = {role: (30.0 if dimensions and role == "left_end" else 0.0,
                      30.0 if dimensions and role in ("left_end", "right_end") else 0.0)
               for role in envelopes}
    def cell_width(role, scale):
        return max(45.0, envelopes[role]["width_mm"] * scale) + sum(padding[role])
    orthographic = [role for role in ("left_end", "longitudinal", "right_end") if role in envelopes]
    usable_width = content["right"] - content["left"]
    usable_height = content["bottom"] - content["top"]

    def fits(scale):
        row_width = sum(cell_width(r, scale) for r in orthographic) + gap * (len(orthographic) - 1)
        row_height = max(envelopes[r]["height_mm"] * scale for r in orthographic)
        iso = envelopes.get("isometric")
        total_height = top_lane + row_height + label_space + (row_gap + iso["height_mm"] * scale + 11 if iso else 0)
        return row_width <= usable_width and total_height <= usable_height and (not iso or iso["width_mm"] * scale <= usable_width)

    scale = next((s for s in PREFERRED_SCALES if fits(s)), None)
    if scale is None:
        raise ValueError("Projected geometry cannot fit the selected sheet at a supported scale")
    row_width = sum(cell_width(r, scale) for r in orthographic) + gap * (len(orthographic) - 1)
    row_height = max(envelopes[r]["height_mm"] * scale for r in orthographic)
    iso = envelopes.get("isometric")
    total_height = top_lane + row_height + label_space + (row_gap + iso["height_mm"] * scale + 11 if iso else 0)
    row_top = content["top"] + (usable_height - total_height) / 2 + top_lane
    row_center = row_top + row_height / 2
    cursor = (width - row_width) / 2
    positions = {}
    for role in orthographic:
        view_width = envelopes[role]["width_mm"] * scale
        view_height = envelopes[role]["height_mm"] * scale
        core_width = max(45.0, view_width)
        center = cursor + padding[role][0] + core_width / 2
        positions[role] = {"x_mm": center, "y_mm": height - row_center,
                           "label_x_mm": center, "label_y_mm": height - row_top - row_height - 7,
                           "expected_width_mm": view_width, "expected_height_mm": view_height}
        cursor += cell_width(role, scale) + gap
    if iso:
        iso_top = row_top + row_height + label_space + row_gap
        positions["isometric"] = {"x_mm": width / 2, "y_mm": height - iso_top - iso["height_mm"] * scale / 2,
                                   "label_x_mm": width / 2, "label_y_mm": height - iso_top - iso["height_mm"] * scale - 7,
                                   "expected_width_mm": iso["width_mm"] * scale, "expected_height_mm": iso["height_mm"] * scale}
    return {"sheet": sheet, "width_mm": width, "height_mm": height, "scale": scale,
            "dimension_lanes_reserved": dimensions, "dimension_top_lane_mm": top_lane,
            "dimension_side_padding_mm": {r: list(p) for r, p in padding.items()},
            "scale_label": f"{scale:g}:1" if scale >= 1 else f"1:{1 / scale:g}",
            "content_area_top_origin_mm": content, "positions": positions,
            "coordinate_note": "TechDraw X/Y positions use a bottom-left page origin"}


def comprehensive_layout(envelopes, discovery, sheet="ANSI-B", requested_scale=None, automatic_sheet=True, decisions=None):
    from .selection import Selection
    selection=Selection(discovery)
    axial={"longitudinal":0,"section":0}
    diameters={'left_end':0,'right_end':0}
    for c in sorted(discovery["dimension_candidates"],key=lambda c:-c["priority"]):
        if decisions is not None and not decisions[c['id']]['selected']:continue
        if c["verification_status"]!="source_measured" or selection.reason(c):continue
        selection.accept(c)
        if c["kind"] in ("overall","axial_distance"):
            role=next((r for r in c["preferred_views"] if r in axial and r in envelopes),"longitudinal")
            axial[role]+=1
        if c['kind'] in ('diameter','curve_diameter'):
            role=next((r for r in c['preferred_views'] if r in envelopes),None)
            if role in diameters:diameters[role]+=1
    top_pad=max(32,axial["longitudinal"]*7+16,20+diameters['left_end']*10,30+diameters['right_end']*10)
    section_pad=max(24,axial["section"]*7+12)
    choices=list(dict.fromkeys([sheet,"ANSI-C","ANSI-D"])) if automatic_sheet else [sheet]
    for selected in choices:
        width,height=SHEETS[selected]
        for scale in ([requested_scale] if requested_scale is not None else (2,2.5,3,1.5,1,.5)):
            # Smaller than 2:1 on tiny fasteners is a last resort after larger
            # supported sheets. Layout aims at readable lanes, not maximum scale.
            if requested_scale is None and selected!=choices[-1] and scale<2:continue
            row_height=max(envelopes[r]["height_mm"]*scale for r in ("left_end","longitudinal","right_end") if r in envelopes)
            second_height=max((envelopes[r]["height_mm"]*(envelopes[r].get('detail_scale',scale)) for r in ("section","isometric","opening_detail") if r in envelopes),default=0)
            roles=[r for r in ("left_end","longitudinal","right_end") if r in envelopes]
            row_width=sum(envelopes[r]["width_mm"]*scale+70 for r in roles)+12*(len(roles)-1)
            total=top_pad+row_height+12+max(section_pad,second_height/2)+second_height/2+30
            if row_width>width-44 or total>height-60:continue
            center_top=18+top_pad+row_height/2
            lower_y=65+second_height/2+10
            # A large profile detail can reach the end-view caption even when
            # both geometry envelopes fit. Reserve a physical caption gap;
            # the native text-bound checks still verify the upper dimension lanes.
            if 'opening_detail' in envelopes:
                detail_top=lower_y+envelopes['opening_detail']['height_mm']*envelopes['opening_detail']['detail_scale']/2
                end_caption=height-center_top-row_height/2-18
                center_top-=max(0,8-(end_caption-detail_top))
            positions={}
            cursor=(width-row_width)/2
            for role in roles:
                w,h=envelopes[role]["width_mm"]*scale,envelopes[role]["height_mm"]*scale
                x=cursor+35+w/2
                positions[role]={"x_mm":x,"y_mm":height-center_top,"label_x_mm":x,"label_y_mm":height-center_top-row_height/2-(18 if role in ('left_end','right_end') else 10),
                                 "expected_width_mm":w,"expected_height_mm":h}
                cursor+=w+82
            lower=[r for r in ("section","isometric","opening_detail") if r in envelopes]
            for index,role in enumerate(lower):
                x=width*({'section':.42,'isometric':.15,'opening_detail':.78}[role] if 'opening_detail' in lower else {'section':.4,'isometric':.77}[role])
                view_scale=envelopes[role].get('detail_scale',scale)
                w,h=envelopes[role]["width_mm"]*view_scale,envelopes[role]["height_mm"]*view_scale
                positions[role]={"x_mm":x,"y_mm":lower_y,"label_x_mm":x,"label_y_mm":lower_y-h/2-12,
                                 "expected_width_mm":w,"expected_height_mm":h,"scale":view_scale}
            return {"sheet":selected,"requested_sheet":sheet,"automatic_sheet_enlargement":selected!=sheet,
                    "sheet_selection_reason":"Compact aligned orthographic row and separate section/profile row; physical text size retained",
                    "width_mm":width,"height_mm":height,"scale":scale,"scale_label":f"{scale:g}:1" if scale>=1 else f"1:{1/scale:g}",
                    "dimension_lanes_reserved":True,"axial_lane_capacity":axial,"dimension_top_lane_mm":top_pad,
                    "content_area_top_origin_mm":{"left":22,"right":width-22,"top":18,"bottom":height-65},
                    "positions":positions,"coordinate_note":"TechDraw X/Y use a bottom-left page origin"}
    raise ValueError("Expanded dimensions cannot fit supported sheets at a readable scale")
