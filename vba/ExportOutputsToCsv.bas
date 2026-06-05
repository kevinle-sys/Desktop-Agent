Attribute VB_Name = "ExportOutputsToCsv"
' Example VBA macro that the VBA/Process agent can also generate.
' Exports the "Outputs" sheet to a timestamped CSV next to the workbook.
Sub ExportOutputsToCsv()
    Dim ws As Worksheet
    Dim outPath As String
    Dim stamp As String

    Set ws = ThisWorkbook.Worksheets("Outputs")
    stamp = Format(Now, "yyyymmdd_hhnnss")
    outPath = ThisWorkbook.Path & Application.PathSeparator & _
              "Outputs_" & stamp & ".csv"

    ws.Copy
    ActiveWorkbook.SaveAs Filename:=outPath, FileFormat:=xlCSV
    ActiveWorkbook.Close SaveChanges:=False

    MsgBox "Exported outputs to " & outPath
End Sub
