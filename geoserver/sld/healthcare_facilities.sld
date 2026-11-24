<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc" 
    xmlns:xlink="http://www.w3.org/1999/xlink" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>healthcare_facilities</Name>
    <UserStyle>
      <Title>PMC Healthcare Facilities Style</Title>
      <Abstract>Hospitals (Red Cross) and Clinics (Cyan Circle) distinct iconography</Abstract>
      <FeatureTypeStyle>
        <!-- Hospitals: Red Cross -->
        <Rule>
          <Name>Hospital</Name>
          <Title>Hospitals</Title>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>subcategory</ogc:PropertyName>
              <ogc:Literal>Hospital</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>cross</WellKnownName>
                <Fill><CssParameter name="fill">#dc2626</CssParameter></Fill>
                <Stroke><CssParameter name="stroke">#991b1b</CssParameter><CssParameter name="stroke-width">1.5</CssParameter></Stroke>
              </Mark>
              <Size>12</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>

        <!-- Clinics: Cyan Circle -->
        <Rule>
          <Name>Clinic</Name>
          <Title>Clinics &amp; Dispensaries</Title>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>subcategory</ogc:PropertyName>
              <ogc:Literal>Clinic</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill><CssParameter name="fill">#06b6d4</CssParameter></Fill>
                <Stroke><CssParameter name="stroke">#ffffff</CssParameter><CssParameter name="stroke-width">1.0</CssParameter></Stroke>
              </Mark>
              <Size>8</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
