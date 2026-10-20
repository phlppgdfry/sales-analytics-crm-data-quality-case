// Reads the semantic model with Microsoft's own TMDL serializer (Microsoft.AnalysisServices.Tabular).
// If the folder is not valid TMDL, deserialisation throws and the exit code is 1.
// It checks structure (tables, columns, relationships, roles, partitions), not whether DAX evaluates.
using Microsoft.AnalysisServices.Tabular;

var folder = args.Length > 0 ? args[0] : "../../powerbi/Vennaert Sales.SemanticModel/definition";
try
{
    var db = TmdlSerializer.DeserializeDatabaseFromFolder(folder);
    var model = db.Model;
    var measures = model.Tables.SelectMany(t => t.Measures).ToList();
    Console.WriteLine($"TMDL OK: {model.Tables.Count} tables, {model.Tables.Sum(t => t.Columns.Count)} columns, " +
                      $"{measures.Count} measures, {model.Relationships.Count} relationships ({model.Relationships.Count(r => !r.IsActive)} inactive), " +
                      $"{model.Roles.Count} roles, compatibility level {db.CompatibilityLevel}");
    foreach (var r in model.Relationships.OfType<SingleColumnRelationship>())
    {
        if (r.FromColumn.Table.Name == r.ToColumn.Table.Name) throw new Exception($"relationship {r.Name} points to its own table");
    }
    return 0;
}
catch (Exception e)
{
    Console.Error.WriteLine($"TMDL INVALID: {e.Message}");
    return 1;
}
